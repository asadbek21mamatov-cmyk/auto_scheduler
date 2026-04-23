from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

TOKEN = "8577675145:AAFPiVWV2mi8wLlh7DRHTX1yHiA0ze0xgWE"

# Scheduler'ni e'lon qilamiz, lekin BU YERDA start qilmaymiz
scheduler = AsyncIOScheduler()

user_state = {}
user_tasks = {}  # {chat_id: [(time, task, job_id_main, job_id_early)]}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.message.chat_id] = None # Holatni tozalash
    await update.message.reply_text(
        "Salom! 👋\n\n"
        "Buyruqlar:\n"
        "/works - ish qo‘shish\n"
        "/list - ishlarni ko‘rish\n"
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
        await update.message.reply_text("❌ O'chirish uchun ishlar yo‘q.")
        user_state[chat_id] = None
        return

    msg = "O‘chirish uchun raqamni tanlang:\n"
    for i, (time_part, task, _, _) in enumerate(tasks):
        msg += f"{i+1}. {time_part} - {task}\n"

    user_state[chat_id] = "waiting_delete"
    await update.message.reply_text(msg)

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    tasks = user_tasks.get(chat_id, [])
    
    for _, _, job1, job2 in tasks:
        try:
            scheduler.remove_job(job1)
        except: pass
        try:
            scheduler.remove_job(job2)
        except: pass

    user_tasks[chat_id] = []
    user_state[chat_id] = None
    await update.message.reply_text("🧹 Barcha ishlar o‘chirildi")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    tasks = user_tasks.get(chat_id, [])

    if not tasks:
        await update.message.reply_text("❌ Ishlar yo‘q")
        user_state[chat_id] = None
        return

    msg = "Sizning ishlaringiz:\n"
    for i, (time_part, task, _, _) in enumerate(tasks):
        msg += f"{i+1}. {time_part} - {task}\n"

    user_state[chat_id] = None
    await update.message.reply_text(msg)

# Xabar yuborish funksiyasi
async def send_reminder(bot, chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print(f"Xabar yuborishda xatolik: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text
    state = user_state.get(chat_id)

    # ➕ Ish qo‘shish
    if state == "waiting_work":
        try:
            time_part, task = text.split("-", 1)
            time_part = time_part.strip()
            task = task.strip()

            hour, minute = map(int, time_part.split(":"))
            now = datetime.now()
            
            # Rejalashtirilgan vaqtni bugungi kunga sozlash
            run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Agar kiritilgan vaqt bugun uchun o'tib ketgan bo'lsa, ertangi kunga o'tkazish
            if run_time <= now:
                run_time += timedelta(days=1)

            reminder_time = run_time - timedelta(minutes=30)

            # Job ID lar
            job_id_main = f"{chat_id}_{now.timestamp()}_main"
            job_id_early = f"{chat_id}_{now.timestamp()}_early"

            # Asosiy xabar
            scheduler.add_job(
                send_reminder,
                'date',
                run_date=run_time,
                args=[context.bot, chat_id, f"⏰ VAQTI KELDI: {task}"],
                id=job_id_main
            )

            # Agar 30 daqiqa oldingi vaqt ham kelajakda bo'lsa, uni qo'shamiz
            if reminder_time > now:
                scheduler.add_job(
                    send_reminder,
                    'date',
                    run_date=reminder_time,
                    args=[context.bot, chat_id, f"⚠️ 30 daqiqadan keyin: {task}"],
                    id=job_id_early
                )
            else:
                job_id_early = None # Oldindan ogohlantirishga ulgurilmasa

            user_tasks.setdefault(chat_id, []).append(
                (time_part, task, job_id_main, job_id_early)
            )

            user_state[chat_id] = None # Holatni tozalash
            await update.message.reply_text(f"✅ Qo‘shildi: {time_part} - {task}")

        except ValueError:
            await update.message.reply_text("❌ Format noto‘g‘ri. Iltimos shunday yozing: 9:00 - Kursga borish")
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik yuz berdi: {e}")

    # ❌ Ish o‘chirish
    elif state == "waiting_delete":
        try:
            index = int(text) - 1
            tasks = user_tasks.get(chat_id, [])
            
            if 0 <= index < len(tasks):
                _, _, job_main, job_early = tasks[index]

                try:
                    scheduler.remove_job(job_main)
                except: pass
                if job_early:
                    try:
                        scheduler.remove_job(job_early)
                    except: pass

                tasks.pop(index)
                user_state[chat_id] = None
                await update.message.reply_text("🗑 O‘chirildi")
            else:
                await update.message.reply_text("❌ Noto‘g‘ri raqam. Qaytadan urinib ko'ring.")
        except ValueError:
            await update.message.reply_text("❌ Faqat raqam kiriting.")

# Botingiz ishga tushganda scheduler'ni ham ishga tushirish uchun funksiya
async def on_startup(app):
    scheduler.start()
    print("Scheduler ishga tushdi...")

if __name__ == '__main__':
    # post_init orqali bot to'liq ishga tushgach, on_startup ishlaydi
    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("works", works))
    app.add_handler(CommandHandler("list", list_tasks)) # List komandasi qo'shildi
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot ishga tushirilmoqda...")
    app.run_polling()
