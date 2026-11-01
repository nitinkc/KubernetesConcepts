// inventory (Node / Express) — catalog + stock reads on the SHARED commerce-db.
// It owns the inventory schema; orders writes into it directly (shared-schema tension).
const express = require('express');
const { Pool } = require('pg');

const app = express();
const log = (severity, message, extra = {}) =>
  console.log(JSON.stringify({ severity, message, domain: 'inventory', ...extra }));

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
// postgres://inventory_rw:...@commerce-db.dom-data:5432/commerce?sslmode=disable

app.get('/healthz', (_, r) => r.send('ok'));
app.get('/readyz', async (_, r) => {
  try {
    await pool.query('SELECT 1');
    r.send('ok');
  } catch (e) {
    r.status(503).send('db down');
  }
});
app.get('/work', (_, r) => {
  log('INFO', 'work called');
  r.json({ ok: true });
});

// NUMERIC comes back as a string in node-pg (precision); cast to float8 so the
// API contract is a JSON number for all callers (Go orders unmarshals float64).
const ITEM_COLS = 'id, sku, name, stock, price::float8 AS price';

app.get('/items', async (_, r) => {
  const { rows } = await pool.query(
    `SELECT ${ITEM_COLS} FROM inventory.items ORDER BY id`
  );
  r.json(rows);
});

app.get('/items/:id', async (req, r) => {
  const { rows } = await pool.query(
    `SELECT ${ITEM_COLS} FROM inventory.items WHERE id = $1`,
    [req.params.id]
  );
  if (!rows.length) return r.status(404).json({ error: 'item not found' });
  log('INFO', 'item fetched', { item_id: req.params.id, stock: rows[0].stock });
  r.json(rows[0]);
});

app.listen(8080, () => log('INFO', 'inventory listening', { port: 8080 }));
