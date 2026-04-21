import logging
import os
import asyncio
import httpx
import yt_dlp
import random
import shutil
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("8514379747:AAGDl0ajvUE157gUa46XoKmca5q0s6RP3yg")
SHRINKME_API = os.getenv("SHRINKME_API", "e985afe0b57e6f737cb84e3109b2fbee91b93c32")
ADMIN = os.getenv("ADMIN", "@qodircg")

APOLOGY_MESSAGES = [
    "😅 Kechirasiz, xayolim Marsga uchib ketgan edi!",
    "🤖 Xayolimdagi robotlar videoni yeyib qo'yishdi!",
    "🐱 Xayolimdagi mushuk kodlarni buzib tashladi.",
    "🎈 Xayolim uchib ketdi, hozir qaytarib olaman...",
    "🍕 Xayolim pitsa yetkazib berish haqida edi!",
    "💤 Xayolim uxlab qolgan ekan...",
    "🌀 Xayolim girdobga tushib ketdi."
]

async def random_apology() -> str:
    return random.choice(APOLOGY_MESSAGES)

def is_instagram(url: str) -> bool:
    patterns = [
        r'(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|tv)/',
        r'(?:https?://)?(?:www\.)?instagr\.am/(?:p|reel|tv)/'
    ]
    return any(re.search(pattern, url) for pattern in patterns)

def is_youtube(url: str) -> bool:
    patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/'
    ]
    return any(re.search(pattern, url) for pattern in patterns)

async def download_instagram(url: str, folder: str):
    os.makedirs(folder, exist_ok=True)
    opts = {
        'outtmpl': folder + '/video.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    loop = asyncio.get_event_loop()
    def go():
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    await loop.run_in_executor(None, go)
    result = []
    for f in os.listdir(folder):
        if f.endswith(('.mp4', '.webm', '.mkv', '.mov')):
            result.append(os.path.join(folder, f))
    return sorted(result)

async def download_youtube(url: str, folder: str):
    os.makedirs(folder, exist_ok=True)
    loop = asyncio.get_event_loop()
    opts = {
        "outtmpl": folder + "/video.%(ext)s",
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4"
    }
    def go():
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([url])
    await loop.run_in_executor(None, go)
    result = []
    for f in os.listdir(folder):
        if f.endswith(('.mp4', '.webm', '.mkv')):
            result.append(os.path.join(folder, f))
    return sorted(result)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Salom! Video yuklab beruvchi bot!\n\n"
        "📥 Qo'llab-quvvatlanadi:\n"
        "• YouTube (video va shorts)\n"
        "• Instagram (reels)\n\n"
        "🔗 Linkni yuboring!"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    uid = update.effective_user.id
    msg = await update.message.reply_text("📥 Yuklanmoqda...")
    folder = f"/tmp/video_{uid}"
    
    try:
        if is_instagram(url):
            await msg.edit_text("📸 Instagram yuklanmoqda...")
            files = await download_instagram(url, folder)
        elif is_youtube(url):
            await msg.edit_text("🎬 YouTube yuklanmoqda...")
            files = await download_youtube(url, folder)
        else:
            apology = await random_apology()
            await msg.edit_text(f"❌ Faqat YouTube/Instagram linki! {apology}")
            return
        
        if not files:
            apology = await random_apology()
            await msg.edit_text(f"❌ Video topilmadi! {apology}")
            return
        
        await msg.edit_text("☁️ Link tayyorlanmoqda...")
        links = []
        for f in files:
            u = await catbox(f)
            if u:
                s = await shorten(u)
                links.append(s)
        
        if links:
            text = "✅ Tayyor!\n\n"
            for i, l in enumerate(links, 1):
                text += f"{i}. {l}\n"
            await msg.edit_text(text)
        else:
            apology = await random_apology()
            await msg.edit_text(f"❌ Xatolik! {apology}")
    except Exception as e:
        logger.exception(e)
        apology = await random_apology()
        await msg.edit_text(f"⚠️ Xatolik! {apology}")
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

async def other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔗 YouTube yoki Instagram linkini yuboring!")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.run_polling()

if __name__ == "__main__":
    main()
