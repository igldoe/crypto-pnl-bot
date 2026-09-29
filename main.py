import os

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from db import add_trade, clear_trades, get_symbols, get_trades, init_db
from pnl import compute_symbol_pnl, fetch_current_prices

HELP_TEXT = (
    "/buy SYMBOL AMOUNT PRICE - записать покупку\n"
    "/sell SYMBOL AMOUNT PRICE - записать продажу\n"
    "/pnl - посчитать PnL по всем монетам\n"
    "/positions - открытые позиции\n"
    "/reset - удалить все свои сделки\n\n"
    "Или просто жми кнопки внизу."
)

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["Купить", "Продать"],
        ["PnL", "Позиции"],
        ["Сброс"],
    ],
    resize_keyboard=True,
)

SYMBOL, AMOUNT, PRICE = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Считаю PnL по твоим сделкам.\n\n" + HELP_TEXT, reply_markup=MAIN_MENU
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, reply_markup=MAIN_MENU)


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


async def trade_start(update: Update, context: ContextTypes.DEFAULT_TYPE, side: str):
    context.user_data["side"] = side
    await update.message.reply_text("Какой тикер? (например BTC)", reply_markup=ReplyKeyboardRemove())
    return SYMBOL


async def trade_start_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await trade_start(update, context, "buy")


async def trade_start_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await trade_start(update, context, "sell")


async def trade_ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["symbol"] = update.message.text.strip()
    await update.message.reply_text("Сколько монет?")
    return AMOUNT


async def trade_ask_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["amount"] = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Введи число, например 0.1")
        return AMOUNT

    await update.message.reply_text("По какой цене (USD)?")
    return PRICE


async def trade_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Введи число, например 60000")
        return PRICE

    side = context.user_data["side"]
    symbol = context.user_data["symbol"]
    amount = context.user_data["amount"]
    add_trade(update.effective_user.id, symbol, side, amount, price)
    await update.message.reply_text(
        f"Записано: {side} {amount} {symbol.upper()} по {price}", reply_markup=MAIN_MENU
    )
    return ConversationHandler.END


async def trade_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено", reply_markup=MAIN_MENU)
    return ConversationHandler.END


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    init_db()

    app = Application.builder().token(token).build()

    trade_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Купить$"), trade_start_buy),
            MessageHandler(filters.Regex("^Продать$"), trade_start_sell),
        ],
        states={
            SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, trade_ask_amount)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, trade_ask_price)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, trade_finish)],
        },
        fallbacks=[CommandHandler("cancel", trade_cancel)],
    )

    app.add_handler(trade_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(CommandHandler("pnl", pnl))
    app.add_handler(CommandHandler("positions", positions))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.Regex("^PnL$"), pnl))
    app.add_handler(MessageHandler(filters.Regex("^Позиции$"), positions))
    app.add_handler(MessageHandler(filters.Regex("^Сброс$"), reset))

    app.run_polling()


if __name__ == "__main__":
    main()
