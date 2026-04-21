from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

TOKEN = "8577675145:AAFPiVWV2mi8wLlh7DRHTX1yHiA0ze0xgWE"

scheduler = AsyncIOScheduler()
scheduler.start()

user_state = {}
user_tasks = {}  # {chat_id: [(time, task, job_id1, job_id2)]}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋\n\n"
        "Buyruqlar:\n"
        "/works - ish qo‘shish\n"
        "/delete - ish o‘chirish\n"
        "/clear - barcha ishlarni o‘chirish\n\n"
        "Misol: 9:00 - Kursga borish"
    )


async def works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.message.chat_id] = "waiting_work"
    await update.message.reply_text("Ishingizni kiriting:\nMisol: 9:00 - Kursga borish")


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    tasks = user_tasks.get(chat_id, [])

    if not tasks:
        await update.message.reply_text("❌ Ishlar yo‘q")
        return

    msg = "O‘chirish uchun raqamni tanlang:\n"
    for i, (time, task, _, _) in enumerate(tasks):
        msg += f"{i+1}. {time} - {task}\n"

    user_state[chat_id] = "waiting_delete"
    await update.message.reply_text(msg)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    tasks = user_tasks.get(chat_id, [])
    for _, _, job1, job2 in tasks:
        try:
            scheduler.remove_job(job1)
            scheduler.remove_job(job2)
        except:
            pass

    user_tasks[chat_id] = []
    await update.message.reply_text("🧹 Barcha ishlar o‘chirildi")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    # ➕ Ish qo‘shish
    if user_state.get(chat_id) == "waiting_work":
        try:
            time_part, task = text.split("-")
            time_part = time_part.strip()
            task = task.strip()

            hour, minute = map(int, time_part.split(":"))

            now = datetime.now()
            run_time = now.replace(hour=hour, minute=minute, second=0)

            if run_time < now:
                await update.message.reply_text("❌ Bu vaqt o‘tib ketgan")
                return

            reminder_time = run_time - timedelta(minutes=30)

            job_id_main = f"{chat_id}_{time_part}_{task}_main"
            job_id_early = f"{chat_id}_{time_part}_{task}_early"

            scheduler.add_job(
                send_reminder,
                'date',
                run_date=run_time,
                args=[context.bot, chat_id, f"⏰ {task}"],
                id=job_id_main
            )

            scheduler.add_job(
                send_reminder,
                'date',
                run_date=reminder_time,
                args=[context.bot, chat_id, f"⚠️ 30 daqiqadan keyin: {task}"],
                id=job_id_early
            )

            user_tasks.setdefault(chat_id, []).append(
                (time_part, task, job_id_main, job_id_early)
            )

            await update.message.reply_text(f"✅ Qo‘shildi: {time_part} - {task}")

        except:
            await update.message.reply_text("❌ Format noto‘g‘ri. Misol: 9:00 - Kursga borish")

    # ❌ Ish o‘chirish
    elif user_state.get(chat_id) == "waiting_delete":
        try:
            index = int(text) - 1
            task = user_tasks[chat_id][index]

            scheduler.remove_job(task[2])
            scheduler.remove_job(task[3])

            user_tasks[chat_id].pop(index)

            await update.message.reply_text("🗑 O‘chirildi")

        except:
            await update.message.reply_text("❌ Noto‘g‘ri raqam")


async def send_reminder(bot, chat_id, text):
    await bot.send_message(chat_id=chat_id, text=text)


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("works", works))
app.add_handler(CommandHandler("delete", delete))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot ishga tushdi...")
app.run_polling()
