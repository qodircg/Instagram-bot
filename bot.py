import logging
import os
import asyncio
import httpx
import yt_dlp
import random
import shutil
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
SHRINKME_API = os.getenv("SHRINKME_API", "e985afe0b57e6f737cb84e3109b2fbee91b93c32")
ADMIN = "@qodircg"

# Qiziqarli uzr so'rash matnlari
APOLOGY_MESSAGES = [
    "😅 Kechirasiz, xayolim bir zumda Marsga uchib ketgan edi. Marsliklar video yuklashda yordam berishmadi... Qaytadan urunib ko'ring!",
    "🤖 Xayolimdagi robotlar videoni yeyib qo'yishdi! Kechirasiz, qayta uruning.",
    "🐱 Xayolimdagi mushuk klaviaturada yurib, kodlarni buzib tashladi. Kechirasiz! Admin bilan bog'lanishingiz mumkin: " + ADMIN,
    "🎈 Xayolim uchib ketdi, hozir uni qaytarib olishga harakat qilaman... Ammo video yuklanmadi. Iltimos, keyinroq urunib ko'ring!",
    "🍕 Xayolim pitsa yetkazib berish haqida edi, shu sababli videoni yuklay olmadim. Kechirasiz!",
    "💤 Xayolim uxlab qolgan ekan... Men uni uyg'otishga urinaman. Siz esa qaytadan urinib ko'ring!",
    "🌀 Xayolim girdobga tushib ketdi. Videoni saqlab qololmadi. Kechirasiz!",
    "🎮 Xayolim video o'yin o'ynab yuribdi, ishga kelishni unutibdi. Kechirasiz, qaytadan uruning."
]

async def random_apology() -> str:
    """Tasodifiy qiziqarli uzr matnini qaytaradi"""
    return random.choice(APOLOGY_MESSAGES)

async def shorten(url):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(
                "https://shrinkme.io/api",
                params={"api": SHRINKME_API, "url": url},
                timeout=10,
            )
            d = r.json()
            if d.get("status") == "success":
                return d["shortenedUrl"]
    except Exception as e:
        logger.error(e)
    return url

async def catbox(path):
    try:
        async with httpx.AsyncClient() as c:
            with open(path, "rb") as f:
                r = await c.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": f},
                    timeout=120,
                )
                return r.text.strip()
    except Exception as e:
        logger.error(e)
    return ""

async def download(url, folder):
    os.makedirs(folder, exist_ok=True)
    opts = {
        "outtmpl": folder + "/video.%(ext)s",
        "format": "18/22/best",
        "quiet": True,
        "no_warnings": True,
    }
    loop = asyncio.get_event_loop()

    def go():
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([url])

    await loop.run_in_executor(None, go)
    result = []
    for f in os.listdir(folder):
        if f.endswith((".mp4", ".webm", ".mkv")):
            result.append(os.path.join(folder, f))
    return sorted(result)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! YouTube video linkini yuboring!\n"
        "Agar xato chiqsa, xayolim adashib qolgan bo'lishi mumkin 😅\n"
        "Muammo: " + ADMIN
    )

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    uid = update.effective_user.id
    msg = await update.message.reply_text("Yuklanmoqda, kuting...")
    folder = "/tmp/yt_" + str(uid)
    try:
        files = await download(url, folder)
        if not files:
            apology = await random_apology()
            await msg.edit_text(f"Video topilmadi! {apology}")
            return
        await msg.edit_text("Link tayyorlanmoqda...")
        links = []
        for f in files:
            u = await catbox(f)
            if u:
                s = await shorten(u)
                links.append(s)
        if links:
            text = "Tayyor! Reklama korib yuklab oling:\n\n"
            for i, l in enumerate(links, 1):
                text += str(i) + ". " + l + "\n"
            await msg.edit_text(text)
        else:
            apology = await random_apology()
            await msg.edit_text(f"Xatolik yuz berdi! {apology}\nAdmin: {ADMIN}")
    except Exception as e:
        logger.exception(e)
        apology = await random_apology()
        await msg.edit_text(f"Kutilmagan xatolik! {apology}\nAdmin: {ADMIN}")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

async def other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apology = await random_apology()
    await update.message.reply_text(f"YouTube linkini yuboring! {apology}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link))
    app.run_polling()

if __name__ == "__main__":
    main()
