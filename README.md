# crypto-pnl-bot

A Telegram bot that tracks profit and loss on your crypto trades. You log your buys and sells, it tells you how much you've made or lost — factoring in current prices.

Built it for myself so I'd stop keeping PnL in notes and spreadsheets. Pulls prices from CoinGecko, stores trades locally in SQLite.

## What it does

- Log buys and sells (by command or through buttons)
- Realized PnL on closed trades, using FIFO
- Unrealized PnL on open positions, against the current price
- Show open positions with average entry price
- Keeps every user's trades separate

Realized profit is closed FIFO: when you sell, the earliest buys go first. Same way it's usually done for taxes.

## Commands

```
/buy SYMBOL AMOUNT PRICE   log a buy
/sell SYMBOL AMOUNT PRICE  log a sell
/pnl                       PnL across all coins
/positions                 open positions
/reset                     wipe all your trades
```

Example:

```
/buy BTC 0.1 60000
/sell BTC 0.05 65000
/pnl
```

Don't feel like remembering the syntax — just hit the buttons and the bot walks you through ticker, amount and price.

## Supported coins

BTC, ETH, SOL, BNB, TON, DOGE, XRP, ADA, USDT, USDC.

Prices come from CoinGecko. To add a coin, drop a couple of lines into `COIN_IDS` in `pnl.py` (the ticker and its CoinGecko id).

## Running it

Needs Python 3.10+ and a bot token from [@BotFather](https://t.me/BotFather).

```bash
git clone https://github.com/igldoe/crypto-pnl-bot.git
cd crypto-pnl-bot
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="your_botfather_token"
python main.py
```

On Windows use `set TELEGRAM_BOT_TOKEN=...` instead of `export`.

Runs on long polling — no server or webhooks needed, just keep the script running.

## How it's laid out

- `main.py` — the bot itself: commands, buttons, step-by-step trade entry
- `pnl.py` — PnL math (FIFO) and CoinGecko price lookups
- `db.py` — trade storage in SQLite
- `requirements.txt` — dependencies

## Heads up

This is a personal bookkeeping tool, not financial advice and not connected to any exchange. You enter trades by hand — whatever you log is what gets counted. CoinGecko prices can differ from your exchange's.
