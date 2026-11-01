# payments (Python / FastAPI) — charge orders, persist to its OWN payments-db.
# Decline is deterministic for drills: simulate=="fail" or an amount ending in .99 -> 402.
import json
import logging
import os
import sys
import time

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class J(logging.Formatter):
    def format(self, r):
        return json.dumps({"severity": r.levelname, "message": r.getMessage(), "domain": "payments"})


h = logging.StreamHandler(sys.stdout)
h.setFormatter(J())
log = logging.getLogger("payments")
log.addHandler(h)
log.setLevel("INFO")

DSN = os.environ["DATABASE_URL"]  # postgres://payments_rw:...@payments-db.dom-data:5432/payments?sslmode=disable

conn = None
for _ in range(30):  # wait for postgres on cold start
    try:
        conn = psycopg.connect(DSN, autocommit=True)
        break
    except Exception as e:
        log.warning(f"waiting for payments-db: {e}")
        time.sleep(2)
if conn is None:
    log.error("cannot reach payments-db")
    sys.exit(1)

app = FastAPI()


class Charge(BaseModel):
    order_id: int
    amount: float
    simulate: str | None = None


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/readyz")
def readyz():
    try:
        conn.execute("SELECT 1")
        return "ok"
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/work")
def work():
    log.info("work called")
    return {"ok": True}


@app.post("/charge", status_code=200)
def charge(c: Charge):
    declined = c.simulate == "fail" or int(round(c.amount * 100)) % 100 == 99
    status = "declined" if declined else "confirmed"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO payments (order_id, amount, status) VALUES (%s,%s,%s) RETURNING id",
            (c.order_id, c.amount, status),
        )
        pid = cur.fetchone()[0]
    if declined:
        log.warning(f"payment declined order_id={c.order_id} amount={c.amount}")
        return JSONResponse({"payment_id": pid, "status": "declined"}, status_code=402)
    log.info(f"payment confirmed order_id={c.order_id} amount={c.amount}")
    return {"payment_id": pid, "status": "confirmed"}


@app.get("/payments/{pid}")
def get_payment(pid: int):
    with conn.cursor() as cur:
        cur.execute("SELECT id, order_id, amount, status FROM payments WHERE id=%s", (pid,))
        row = cur.fetchone()
    if not row:
        return {"error": "not found"}, 404
    return {"id": row[0], "order_id": row[1], "amount": float(row[2]), "status": row[3]}
