// orders (Go) — public-facing order API for the Acme Store.
// Saga: check stock via inventory HTTP -> decrement + order row in shared commerce-db
// (one tx) -> charge payments -> confirm or compensate.
package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	_ "github.com/lib/pq"
)

var lg = slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{ReplaceAttr: func(_ []string, a slog.Attr) slog.Attr {
	if a.Key == "level" {
		a.Key = "severity"
	}
	if a.Key == "msg" {
		a.Key = "message"
	}
	return a
}}))

var db *sql.DB

func jwrite(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func call(u string) int {
	r, err := http.Get(u)
	if err != nil {
		lg.Error("call failed", "url", u, "err", err.Error())
		return 0
	}
	defer r.Body.Close()
	return r.StatusCode
}

type item struct {
	ID    int     `json:"id"`
	SKU   string  `json:"sku"`
	Name  string  `json:"name"`
	Stock int     `json:"stock"`
	Price float64 `json:"price"`
}

type orderReq struct {
	ItemID   int    `json:"item_id"`
	Qty      int    `json:"qty"`
	Simulate string `json:"simulate"` // "fail" forces the payments decline -> compensation drill
}

func getJSON(u string, v any) (int, error) {
	r, err := http.Get(u)
	if err != nil {
		return 0, err
	}
	defer r.Body.Close()
	return r.StatusCode, json.NewDecoder(r.Body).Decode(v)
}

func postJSON(u string, body io.Reader) (int, []byte, error) {
	r, err := http.Post(u, "application/json", body)
	if err != nil {
		return 0, nil, err
	}
	defer r.Body.Close()
	b, _ := io.ReadAll(r.Body)
	return r.StatusCode, b, nil
}

// POST /orders {item_id, qty, simulate}
// 1. HTTP check: inventory /items/:id (stock + price)
// 2. One tx on commerce-db: decrement stock + insert pending order  ("orders reduces inventory")
// 3. POST payments /charge
// 4. confirm, or compensate (restore stock, cancel order)
func createOrder(w http.ResponseWriter, r *http.Request) {
	var req orderReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.ItemID <= 0 || req.Qty <= 0 {
		jwrite(w, http.StatusBadRequest, map[string]string{"error": "need item_id>0 and qty>0"})
		return
	}

	// --- 1. check stock/price through the inventory SERVICE (HTTP, not DB) ---
	var it item
	code, err := getJSON(os.Getenv("INVENTORY_URL")+fmt.Sprintf("/items/%d", req.ItemID), &it)
	if err != nil || code != 200 {
		lg.Error("inventory check failed", "item_id", req.ItemID, "status", code, "err", fmt.Sprint(err))
		jwrite(w, http.StatusBadGateway, map[string]string{"error": "inventory lookup failed"})
		return
	}
	if it.Stock < req.Qty {
		jwrite(w, http.StatusConflict, map[string]any{"error": "insufficient stock", "stock": it.Stock})
		return
	}
	amount := it.Price * float64(req.Qty)

	// --- 2. shared-DB tx: decrement + order row (atomic) ---
	tx, err := db.Begin()
	if err != nil {
		jwrite(w, http.StatusInternalServerError, map[string]string{"error": "db begin failed"})
		return
	}
	res, err := tx.Exec(
		`UPDATE inventory.items SET stock = stock - $1 WHERE id = $2 AND stock >= $1`,
		req.Qty, req.ItemID)
	if err != nil {
		tx.Rollback()
		jwrite(w, http.StatusInternalServerError, map[string]string{"error": "stock update failed"})
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		tx.Rollback() // raced: stock changed between check and decrement
		jwrite(w, http.StatusConflict, map[string]string{"error": "insufficient stock (race)"})
		return
	}
	var orderID int
	err = tx.QueryRow(
		`INSERT INTO sales.orders (item_id, qty, amount, status) VALUES ($1,$2,$3,'pending') RETURNING id`,
		req.ItemID, req.Qty, amount).Scan(&orderID)
	if err != nil {
		tx.Rollback()
		jwrite(w, http.StatusInternalServerError, map[string]string{"error": "order insert failed"})
		return
	}
	if err := tx.Commit(); err != nil {
		jwrite(w, http.StatusInternalServerError, map[string]string{"error": "commit failed"})
		return
	}
	lg.Info("order placed, stock decremented", "domain", "orders", "order_id", orderID, "item_id", req.ItemID, "qty", req.Qty)

	// --- 3. charge payments (separate service, separate DB = real saga boundary) ---
	chargeBody, _ := json.Marshal(map[string]any{"order_id": orderID, "amount": amount, "simulate": req.Simulate})
	pcode, pbody, err := postJSON(os.Getenv("PAYMENTS_URL")+"/charge", strings.NewReader(string(chargeBody)))
	if err == nil && pcode == 200 {
		db.Exec(`UPDATE sales.orders SET status='confirmed', payment_id=$1 WHERE id=$2`, extractID(pbody), orderID)
		lg.Info("order confirmed", "domain", "orders", "order_id", orderID, "amount", amount)
		jwrite(w, http.StatusCreated, map[string]any{"order_id": orderID, "status": "confirmed", "amount": amount})
		return
	}

	// --- 4. compensation: payments failed -> restore stock, cancel order ---
	lg.Warn("payment declined, compensating", "domain", "orders", "order_id", orderID, "pstatus", pcode)
	ct, cerr := db.Begin()
	if cerr == nil {
		ct.Exec(`UPDATE inventory.items SET stock = stock + $1 WHERE id = $2`, req.Qty, req.ItemID)
		ct.Exec(`UPDATE sales.orders SET status='cancelled' WHERE id=$1`, orderID)
		cerr = ct.Commit()
	}
	if cerr != nil {
		lg.Error("COMPENSATION FAILED — manual fix needed", "domain", "orders", "order_id", orderID, "err", cerr.Error())
	} else {
		lg.Info("stock restored via compensation", "domain", "orders", "order_id", orderID)
	}
	jwrite(w, http.StatusPaymentRequired, map[string]any{"order_id": orderID, "status": "cancelled", "reason": "payment declined", "compensated": cerr == nil})
}

func extractID(b []byte) int {
	var v struct {
		PaymentID int `json:"payment_id"`
	}
	json.Unmarshal(b, &v)
	return v.PaymentID
}

func getOrder(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/orders/")
	var o struct {
		ID, ItemID, Qty int
		Amount          float64
		Status          string
		PaymentID       sql.NullInt64
	}
	err := db.QueryRow(`SELECT id,item_id,qty,amount,status,COALESCE(payment_id,0) FROM sales.orders WHERE id=$1`, id).
		Scan(&o.ID, &o.ItemID, &o.Qty, &o.Amount, &o.Status, &o.PaymentID)
	if err != nil {
		jwrite(w, http.StatusNotFound, map[string]string{"error": "order not found"})
		return
	}
	jwrite(w, 200, o)
}

func main() {
	var err error
	dsn := os.Getenv("DATABASE_URL") // postgres://orders_rw:...@commerce-db.dom-data:5432/commerce?sslmode=disable
	for i := 0; i < 30; i++ {        // wait for postgres on cold start
		if db, err = sql.Open("postgres", dsn); err == nil && db.Ping() == nil {
			break
		}
		time.Sleep(2 * time.Second)
	}
	if err != nil || db.Ping() != nil {
		lg.Error("cannot reach commerce-db", "err", fmt.Sprint(err))
		os.Exit(1)
	}

	http.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) { w.Write([]byte("ok")) })
	http.HandleFunc("/readyz", func(w http.ResponseWriter, _ *http.Request) {
		if db.Ping() == nil {
			w.Write([]byte("ok"))
		} else {
			http.Error(w, "db down", 503)
		}
	})
	// /work = legacy call-graph probe (labs 03/05/06 verify matrix)
	http.HandleFunc("/work", func(w http.ResponseWriter, _ *http.Request) {
		p := call(os.Getenv("PAYMENTS_URL") + "/work")
		i := call(os.Getenv("INVENTORY_URL") + "/work")
		lg.Info("work called", "domain", "orders", "payments", p, "inventory", i)
		json.NewEncoder(w).Encode(map[string]int{"payments": p, "inventory": i})
	})
	http.HandleFunc("POST /orders", createOrder)
	http.HandleFunc("GET /orders/", getOrder)
	lg.Info("orders listening", "port", 8080)
	http.ListenAndServe(":8080", nil)
}
