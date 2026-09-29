from collections import deque

import requests

COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "TON": "the-open-network",
    "DOGE": "dogecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "USDT": "tether",
    "USDC": "usd-coin",
}


def compute_symbol_pnl(trades, current_price):
    lots = deque()
    realized = 0.0

    for _sym, side, amount, price, _ts in trades:
        if side == "buy":
            lots.append([amount, price])
        else:
            remaining = amount
            while remaining > 1e-12 and lots:
                lot_amount, lot_price = lots[0]
                matched = min(lot_amount, remaining)
                realized += (price - lot_price) * matched
                lot_amount -= matched
                remaining -= matched
                if lot_amount <= 1e-12:
                    lots.popleft()
                else:
                    lots[0][0] = lot_amount

    open_amount = sum(l[0] for l in lots)
    cost_basis = sum(l[0] * l[1] for l in lots)
    avg_cost = cost_basis / open_amount if open_amount > 1e-12 else 0.0

    unrealized = None
    if current_price is not None and open_amount > 1e-12:
        unrealized = (current_price - avg_cost) * open_amount

    return {
        "realized": realized,
        "open_amount": open_amount,
        "avg_cost": avg_cost,
        "unrealized": unrealized,
    }


def fetch_current_prices(symbols):
    ids_map = {s.upper(): COIN_IDS[s.upper()] for s in symbols if s.upper() in COIN_IDS}
    prices = {s: None for s in symbols}
    if not ids_map:
        return prices

    resp = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": ",".join(ids_map.values()), "vs_currencies": "usd"},
        timeout=10,
    )
    data = resp.json() if resp.ok else {}

    for symbol, cg_id in ids_map.items():
        if cg_id in data:
            prices[symbol] = data[cg_id]["usd"]

    return prices
