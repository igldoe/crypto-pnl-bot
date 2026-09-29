import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from db import add_trade, clear_trades, get_symbols, get_trades, init_db
from pnl import compute_symbol_pnl, fetch_current_prices

HELP_TEXT = (
    "/buy SYMBOL AMOUNT PRICE - записать покупку\n"
    "/sell SYMBOL AMOUNT PRICE - записать продажу\n"
    "/pnl - посчитать PnL по всем монетам\n"
    "/positions - открытые позиции\n"
    "/reset - удалить все свои сделки\n\n"
    "Пример: /buy BTC 0.1 60000"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Считаю PnL по твоим сделкам.\n\n" + HELP_TEXT)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def record_trade(update: Update, context: ContextTypes.DEFAULT_TYPE, side: str):
    args = context.args
    if len(args) != 3:
        await update.message.reply_text(f"Использование: /{side} SYMBOL AMOUNT PRICE")
        return

    symbol, amount_str, price_str = args
    try:
        amount = float(amount_str)
        price = float(price_str)
    except ValueError:
        await update.message.reply_text("AMOUNT и PRICE должны быть числами")
        return

    add_trade(update.effective_user.id, symbol, side, amount, price)
    await update.message.reply_text(f"Записано: {side} {amount} {symbol.upper()} по {price}")


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await record_trade(update, context, "buy")


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await record_trade(update, context, "sell")


async def pnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    symbols = get_symbols(user_id)
    if not symbols:
        await update.message.reply_text("Пока нет сделок")
        return

    prices = fetch_current_prices(symbols)
    lines = []
    total_realized = 0
    total_unrealized = 0

    for symbol in symbols:
        trades = get_trades(user_id, symbol)
        r = compute_symbol_pnl(trades, prices.get(symbol))
        total_realized += r["realized"]
        line = f"{symbol}: реализовано {r['realized']:+.2f} USD"
        if r["open_amount"] > 1e-9:
            line += f", открыто {r['open_amount']:g} @ {r['avg_cost']:.4f}"
            if r["unrealized"] is not None:
                line += f", нереализовано {r['unrealized']:+.2f} USD"
                total_unrealized += r["unrealized"]
        lines.append(line)

    lines.append("")
    lines.append(f"Итого: {total_realized + total_unrealized:+.2f} USD")
    await update.message.reply_text("\n".join(lines))


async def positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lines = []
    for symbol in get_symbols(user_id):
        trades = get_trades(user_id, symbol)
        r = compute_symbol_pnl(trades, None)
        if r["open_amount"] > 1e-9:
            lines.append(f"{symbol}: {r['open_amount']:g} @ {r['avg_cost']:.4f}")

    await update.message.reply_text("\n".join(lines) if lines else "Нет открытых позиций")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_trades(update.effective_user.id)
    await update.message.reply_text("Сделки удалены")


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    init_db()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(CommandHandler("pnl", pnl))
    app.add_handler(CommandHandler("positions", positions))
    app.add_handler(CommandHandler("reset", reset))

    app.run_polling()


if __name__ == "__main__":
    main()
