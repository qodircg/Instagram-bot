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

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
SHRINKME_API = os.getenv("SHRINKME_API", "e985afe0b57e6f737cb84e3109b2fbee91b93c32")
ADMIN = "@qodircg"

# Qiziqarli uzr so'rash matnlari
APOLOGY_MESSAGES = [
    "😅 Kechirasiz, xayolim bir zumda Marsga uchib ketgan edi. Marsliklar video yuklashda yordam berishmadi... Qaytadan urunib ko'ring!",
    "🤖 Xayolimdagi robotlar videoni yeyib qo'yishdi! Kechirasiz, qayta uruning.",
    "🐱 Xayolimdagi mushuk klaviaturada yurib, kodlarni buzib tashladi. Kechirasiz!",
    "🎈 Xayolim uchib ketdi, hozir uni qaytarib olishga harakat qilaman...",
    "🍕 Xayolim pitsa yetkazib berish haqida edi, shu sababli videoni yuklay olmadim!",
    "💤 Xayolim uxlab qolgan ekan... Men uni uyg'otishga urinaman.",
    "🌀 Xayolim girdobga tushib ketdi. Videoni saqlab qololmadi.",
    "🎮 Xayolim video o'yin o'ynab yuribdi, ishga kelishni unutibdi."
]

async def random_apology() -> str:
    return random.choice(APOLOGY_MESSAGES)

def is_instagram(url: str) -> bool:
    """Instagram linkini tekshirish"""
    patterns = [
        r'(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|tv)/',
        r'(?:https?://)?(?:www\.)?instagr\.am/(?:p|reel|tv)/'
    ]
    return any(re.search(pattern, url) for pattern in patterns)

def is_youtube(url: str) -> bool:
    """YouTube linkini tekshirish"""
    patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/'
    ]
    return any(re.search(pattern, url) for pattern in patterns)

async def download_instagram(url: str, folder: str):
    """Instagram'dan video yuklash"""
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
            try:
                ydl.download([url])
            except Exception as e:
                logger.error(f"Instagram download error: {e}")
                raise
    
    await loop.run_in_executor(None, go)
    
    result = []
    for f in os.listdir(folder):
        if f.endswith(('.mp4', '.webm', '.mkv', '.mov')):
            result.append(os.path.join(folder, f))
    return sorted(result)

async def download_youtube(url: str, folder: str):
    """YouTube'dan video yuklash"""
    os.makedirs(folder, exist_ok=True)
    
    loop = asyncio.get_event_loop()
    
    def get_best_format():
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            # Eng yaxshi mp4 formatini topish
            best_format = None
            best_height = 0
            
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    if f.get('ext') == 'mp4':
                        height = f.get('height', 0)
                        if height > best_height:
                            best_height = height
                            best_format = f
            
            if best_format:
                return best_format['format_id']
            
            # Agar mp4+audio topilmasa, istalgan format
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('ext') == 'mp4':
                    return f['format_id']
            
            return 'best'
    
    try:
        format_id = get_best_format()
    except:
        format_id = 'best'
    
    opts = {
        "outtmpl": folder + "/video.%(ext)s",
        "format": format_id,
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
        "🎬 Salom! Men video yuklab beruvchi bot!\n\n"
        "📥 Qo'llab-quvvatlanadigan platformalar:\n"
        "• YouTube (video va shorts)\n"
        "• Instagram (reels va postlar)\n\n"
        "🔗 Menga linkni yuboring, men uni yuklab beraman!\n"
        f"👨‍💻 Muammo: {ADMIN}"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    uid = update.effective_user.id
    msg = await update.message.reply_text("📥 Yuklanmoqda, kuting...")
    folder = "/tmp/video_" + str(uid)
    
    try:
        # Platformani aniqlash
        if is_instagram(url):
            await msg.edit_text("📸 Instagram reels yuklanmoqda...")
            files = await download_instagram(url, folder)
        elif is_youtube(url):
            await msg.edit_text("🎬 YouTube video yuklanmoqda...")
            files = await download_youtube(url, folder)
        else:
            apology = await random_apology()
            await msg.edit_text(f"❌ Faqat YouTube va Instagram linklarini qo'llab-quvvatlayman!\n{apology}")
            return
        
        if not files:
            apology = await random_apology()
            await msg.edit_text(f"❌ Video topilmadi! {apology}")
            return
        
        await msg.edit_text("☁️ Link tayyorlanmoqda (Catboxga yuklanmoqda)...")
        links = []
        
        for f in files:
            u = await catbox(f)
            if u:
                s = await shorten(u)
                links.append(s)
        
        if links:
            text = "✅ Tayyor! Yuklab olish uchun linklar:\n\n"
            for i, l in enumerate(links, 1):
                text += f"{i}. {l}\n"
            await msg.edit_text(text)
        else:
            apology = await random_apology()
            await msg.edit_text(f"❌ Xatolik yuz berdi! {apology}\nAdmin: {ADMIN}")
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"DownloadError: {e}")
        apology = await random_apology()
        await msg.edit_text(f"📥 Video yuklab olishda xatolik! Video maxfiy yoki o'chirilgan bo'lishi mumkin.\n{apology}\nAdmin: {ADMIN}")
        
    except Exception as e:
        logger.exception(e)
        apology = await random_apology()
        await msg.edit_text(f"⚠️ Kutilmagan xatolik! {apology}\nAdmin: {ADMIN}")
        
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

async def other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 Iltimos, YouTube yoki Instagram video linkini yuboring!\n\n"
        "Masalan:\n"
        "• https://youtube.com/watch?v=...\n"
        "• https://youtube.com/shorts/...\n"
        "• https://instagram.com/reel/..."
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.run_polling()

if __name__ == "__main__":
    main()
