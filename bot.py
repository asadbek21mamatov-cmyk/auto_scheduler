from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

TOKEN = "8577675145:AAFPiVWV2mi8wLlh7DRHTX1yHiA0ze0xgWE"

scheduler = AsyncIOScheduler()

user_state = {}
user_tasks = {}

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    tasks = user_tasks.get(chat_id, [])

    if not tasks:
        await update.message.reply_text("📭 Hozircha ishlar yo‘q")
        return

    msg = "📋 Sening ishlaring:\n\n"
    for i, (time_part, task, _, _) in enumerate(tasks):
        msg += f"{i+1}. ⏰ {time_part} - {task}\n"

    await update.message.reply_text(msg)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! 👋")


async def works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.message.chat_id] = "waiting_work"
    await update.message.reply_text("Misol: 9:00 - Kursga borish")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    if user_state.get(chat_id) == "waiting_work":
        try:
            time_part, task = text.split("-")
            time_part = time_part.strip()
            task = task.strip()

            hour, minute = map(int, time_part.split(":"))

            now = datetime.now()
            run_time = now.replace(hour=hour, minute=minute, second=0)

            reminder_time = run_time - timedelta(minutes=30)

            scheduler.add_job(
                send_reminder,
                'date',
                run_date=run_time,
                args=[context.bot, chat_id, f"⏰ {task}"]
            )

            scheduler.add_job(
                send_reminder,
                'date',
                run_date=reminder_time,
                args=[context.bot, chat_id, f"⚠️ 30 daqiqadan keyin: {task}"]
            )

            await update.message.reply_text("✅ Qo‘shildi")

        except:
            await update.message.reply_text("❌ Format xato")


async def send_reminder(bot, chat_id, text):
    await bot.send_message(chat_id=chat_id, text=text)


# 🔥 MUHIM JOY
async def post_init(app):
    print("Scheduler start bo‘ldi")
    scheduler.start()


app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("works", works))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("list", list_tasks))
print("Bot ishga tushdi...")
app.run_polling()
