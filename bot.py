import logging
import os
import re
import asyncio
import httpx
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters
from telegram.ext import ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
SHRINKME_API = os.getenv("SHRINKME_API", "e985afe0b57e6f737cb84e3109b2fbee91b93c32")
ADMIN = "@qodircg"
IG_RE = re.compile(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)")


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
        "outtmpl": folder + "/%(id)s.%(ext)s",
        "format": "best[ext=mp4]/best",
        "quiet": True,
    }
    loop = asyncio.get_event_loop()

    def go():
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([url])

    await loop.run_in_executor(None, go)
    result = []
    for f in os.listdir(folder):
        if f.endswith((".mp4", ".jpg", ".png")):
            result.append(os.path.join(folder, f))
    return sorted(result)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Instagram reel yoki post linkini yuboring!\nMuammo: " + ADMIN
    )


async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    uid = update.effective_user.id
    if not IG_RE.search(url):
        await update.message.reply_text("Instagram linki emas!")
        return
    msg = await update.message.reply_text("Yuklanmoqda...")
    folder = "/tmp/ig_" + str(uid)
    try:
        files = await download(url, folder)
        if not files:
            await msg.edit_text("Media topilmadi!")
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
            await msg.edit_text("Xatolik! " + ADMIN)
    except Exception as e:
        logger.exception(e)
        await msg.edit_text("Xatolik! " + ADMIN)
    finally:
        import shutil
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)


async def other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Instagram linkini yuboring!")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"instagram\.com"), link))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, other))
    app.run_polling()


if __name__ == "__main__":
    main()
