import logging, os, re, asyncio, httpx, yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8514379747:AAGDl0ajvUE157gUa46XoKmca5q0s6RP3yg")
SHRINKME_API = os.getenv("SHRINKME_API", "e985afe0b57e6f737cb84e3109b2fbee91b93c32")
ADMIN_ID = "@qodircg"

INSTAGRAM_RE = re.compile(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)")

async def shorten_url(long_url):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://shrinkme.io/api", params={"api": SHRINKME_API, "url": long_url}, timeout=10)
            data = r.json()
            if data.get("status") == "success":
                return data["shortenedUrl"]
    except Exception as e:
        logger.error(f"Shrinkme error: {e}")
    return long_url

async def upload_to_catbox(file_path):
    try:
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                r = await client.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=120)
                return r.text.strip()
    except Exception as e:
        logger.error(f"Catbox error: {e}")
    return ""

async def download_instagram(url, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    ydl_opts = {
        "outtmpl": f"{target_dir}/%(id)s.%(ext)s",
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
    }
    loop = asyncio.get_event_loop()
    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    await loop.run_in_executor(None, _download)
    files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith((".mp4", ".jpg", ".jpeg", ".png"))]
    return sorted(files)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Salom! Instagram post yoki reel linkini yuboring!\n\nMuammo bo'lsa: " + ADMIN_ID)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user = update.effective_user
    if not INSTAGRAM_RE.search(url):
        await update.message.reply_text("❌ Instagram linki tanib olinmadi.")
        return
    status_msg = await update.message.reply_text("⏳ Yuklanmoqda, kuting...")
    target_dir = f"/tmp/ig_{user.id}_{int(asyncio.get_event_loop().time())}"
    try:
        media_files = await download_instagram(url, target_dir)
        if not media_files:
            await status_msg.edit_text("❌ Media topilmadi.")
            return
        await status_msg.edit_text("🔗 Linklar tayyorlanmoqda...")
        links = []
        for fpath in media_files:
            direct_url = await upload_to_catbox(fpath)
            if direct_url:
                short_url = await shorten_url(direct_url)
                links.append(short_url)
        if links:
            msg = "✅ Tayyor! Yuklab olish uchun:\n\n"
            for i, link in enumerate(links, 1):
                msg += f"📥 {i}-video: {link}\n"
            msg += "\n⚠️ Linkga bosing, qisqa reklama ko'ring va yuklab oling!"
            await status_msg.edit_text(msg)
        else:
            await status_msg.edit_text(f"❌ Xatolik. {ADMIN_ID} ga murojaat qiling.")
    except Exception as e:
        logger.exception(e)
        await status_msg.edit_text(f"❌ Xatolik yuz berdi. {ADMIN_ID} ga murojaat qiling.")
    finally:
        if os.path.exists(target_dir):
            import shutil
            shutil.rmtree(target_dir, ignore_errors=True)

async def handle_non_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📎 Instagram linkini yuboring!\nMasalan: https://www.instagram.com/reel/ABC123/")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"instagram\.com"), handle_url))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_url))
    logger.info("​​​​​​​​​​​​​​​​
