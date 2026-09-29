import sqlite3

DB_PATH = "pnl.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            amount REAL NOT NULL,
            price REAL NOT NULL,
            ts TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def add_trade(user_id, symbol, side, amount, price):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO trades (user_id, symbol, side, amount, price) VALUES (?, ?, ?, ?, ?)",
        (user_id, symbol.upper(), side, amount, price),
    )
    conn.commit()
    conn.close()


def get_trades(user_id, symbol=None):
    conn = sqlite3.connect(DB_PATH)
    if symbol:
        rows = conn.execute(
            "SELECT symbol, side, amount, price, ts FROM trades WHERE user_id=? AND symbol=? ORDER BY ts",
            (user_id, symbol.upper()),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT symbol, side, amount, price, ts FROM trades WHERE user_id=? ORDER BY ts",
            (user_id,),
        ).fetchall()
    conn.close()
    return rows


def get_symbols(user_id):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT DISTINCT symbol FROM trades WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows]


def clear_trades(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM trades WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
