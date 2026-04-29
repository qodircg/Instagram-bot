import logging
import os
import asyncio
import httpx
import yt_dlp
import sqlite3
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
SHRINKME_API = os.getenv("SHRINKME_API", "e985afe0b57e6f737cb84e3109b2fbee91b93c32")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1310172108"))
CHANNEL = "@qodir_cg"
DAILY_LIMIT = 5
DELETE_AFTER = 600  # 10 daqiqa

# ─── Tillar ─────────────────────────────────────────────────────────────────
TEXTS = {
    "uz": {
        "start": "👋 Assalomu alaykum, {name}!\n\n🎬 Men YouTube, TikTok va Pinterest dan video va musiqa yuklab beraman!\n\n📌 Ishlating:\n• YouTube/TikTok/Pinterest linkini yuboring\n• Yoki musiqa nomini yozing\n\n🏆 Sizning ballingiz: {points} ⭐\n👥 Taklif qilganlar: {refs} ta",
        "choose_lang": "🌐 Tilni tanlang / Выберите язык / Забонро интихоб кунед:",
        "sub_required": "⚠️ Botdan foydalanish uchun kanalga obuna bo'ling!\n\n📢 Kanal: {channel}\n\nObuna bo'lgach ✅ Tekshirish tugmasini bosing.",
        "sub_check": "✅ Tekshirish",
        "sub_ok": "✅ Obuna tasdiqlandi! Endi linkni yuboring.",
        "sub_fail": "❌ Siz hali obuna bo'lmagansiz!\n\n📢 {channel} kanaliga obuna bo'ling.",
        "banned": "🚫 Siz botdan bloklangansiz.\n\nMurojaat: @qodircg",
        "bot_off": "🔴 Bot hozir ishlamayapti. Keyinroq urinib ko'ring.",
        "limit": "⚠️ Kunlik limitingiz tugadi!\n\n📊 Kunlik limit: {limit} ta video\n🔄 Limit ertaga yangilanadi.",
        "sending_link": "🔗 Havola tayyorlanmoqda...",
        "downloading": "⏳ Yuklanmoqda...\n\n🔗 {url}",
        "choose_quality": "🎬 Sifatni tanlang:",
        "choose_format": "🎵 Formatni tanlang:",
        "size_info": "📦 Taxminiy hajm: {size}\n⏱ Davomiyligi: {duration}\n👁 Ko'rishlar: {views}\n\n📥 Formatni tanlang:",
        "done": "✅ Tayyor!\n\n📥 Yuklab olish:\n{link}\n\n⚠️ Havola {minutes} daqiqadan keyin o'chadi!\n\n🏆 +1 ball qo'shildi! Jami: {points} ⭐",
        "error": "😔 Kechirasiz, bu videoni yuklab bo'lmadi.\n\nQuyidagi sabab bo'lishi mumkin:\n• Video yopiq/private\n• Link noto'g'ri\n• Server muammosi\n\n🔄 Boshqa link bilan urinib ko'ring.",
        "music_search": "🎵 Musiqa qidirilmoqda: {query}",
        "music_results": "🎵 Natijalar:",
        "no_results": "😔 Hech narsa topilmadi.",
        "ref_link": "👥 Do'stlaringizni taklif qiling!\n\n🔗 Sizning havola:\n{link}\n\n🏆 Har taklif uchun +5 ball!\n👥 Taklif qilganlar: {count} ta",
        "new_ref": "🎉 Yangi do'st qo'shildi! +5 ball!\nJami: {points} ⭐",
        "top": "🏆 Top 10 foydalanuvchilar:\n\n{list}",
        "profile": "👤 Profil\n\n🆔 ID: {id}\n👤 Ism: {name}\n🌐 Til: {lang}\n🏆 Ball: {points} ⭐\n📥 Yuklab olishlar: {downloads}\n👥 Taklif: {refs}\n📅 Ro'yxat: {date}",
        "trim_ask": "✂️ Video qisqartirish uchun vaqtni kiriting:\nFormat: `boshlanish tugash`\nMasalan: `0:30 1:00`",
        "trim_processing": "✂️ Video qisqartirilmoqda...",
        "ad_set": "✅ Reklama matni o'rnatildi!",
        "ad_del": "✅ Reklama o'chirildi!",
        "broadcast_done": "📢 Xabar {count} ta foydalanuvchiga yuborildi!",
        "stats": "📊 Statistika\n\n👥 Jami foydalanuvchilar: {users}\n📥 Bugungi yuklab olishlar: {today}\n📅 Oylik yuklab olishlar: {month}\n🚫 Banlangan: {banned}\n🌐 Tillar:\n  🇺🇿 O'zbek: {uz}\n  🇷🇺 Rus: {ru}\n  🇹🇯 Tojik: {tj}",
        "ban_done": "🚫 Foydalanuvchi {id} bloklandi!",
        "unban_done": "✅ Foydalanuvchi {id} blokdan chiqarildi!",
        "bot_stopped": "🔴 Bot to'xtatildi!",
        "bot_started": "🟢 Bot yoqildi!",
        "help": "📖 Yordam\n\n🎬 Video yuklab olish:\nYouTube, TikTok yoki Pinterest linkini yuboring\n\n🎵 Musiqa qidirish:\n/music [nom] yoki [qo'shiqchi]\n\n👥 Do'st taklif:\n/ref\n\n🏆 Reyting:\n/top\n\n👤 Profil:\n/profile\n\n✂️ Video qisqartirish:\n/trim [link]",
    },
    "ru": {
        "start": "👋 Привет, {name}!\n\n🎬 Я скачиваю видео и музыку с YouTube, TikTok и Pinterest!\n\n📌 Использование:\n• Отправьте ссылку YouTube/TikTok/Pinterest\n• Или напишите название музыки\n\n🏆 Ваши баллы: {points} ⭐\n👥 Приглашено: {refs}",
        "sub_required": "⚠️ Для использования бота подпишитесь на канал!\n\n📢 Канал: {channel}\n\nПосле подписки нажмите ✅ Проверить.",
        "sub_check": "✅ Проверить",
        "sub_ok": "✅ Подписка подтверждена! Теперь отправьте ссылку.",
        "sub_fail": "❌ Вы ещё не подписались!\n\n📢 Подпишитесь на {channel}.",
        "banned": "🚫 Вы заблокированы.\n\nПо вопросам: @qodircg",
        "bot_off": "🔴 Бот временно недоступен. Попробуйте позже.",
        "limit": "⚠️ Дневной лимит исчерпан!\n\n📊 Лимит: {limit} видео в день\n🔄 Лимит обновится завтра.",
        "sending_link": "🔗 Подготовка ссылки...",
        "downloading": "⏳ Загрузка...\n\n🔗 {url}",
        "choose_quality": "🎬 Выберите качество:",
        "choose_format": "🎵 Выберите формат:",
        "size_info": "📦 Примерный размер: {size}\n⏱ Длительность: {duration}\n👁 Просмотры: {views}\n\n📥 Выберите формат:",
        "done": "✅ Готово!\n\n📥 Скачать:\n{link}\n\n⚠️ Ссылка удалится через {minutes} минут!\n\n🏆 +1 балл! Итого: {points} ⭐",
        "error": "😔 Извините, не удалось загрузить видео.\n\nВозможные причины:\n• Видео закрытое/private\n• Неверная ссылка\n• Проблема с сервером\n\n🔄 Попробуйте другую ссылку.",
        "music_search": "🎵 Поиск музыки: {query}",
        "music_results": "🎵 Результаты:",
        "no_results": "😔 Ничего не найдено.",
        "ref_link": "👥 Пригласите друзей!\n\n🔗 Ваша ссылка:\n{link}\n\n🏆 +5 баллов за каждого!\n👥 Приглашено: {count}",
        "new_ref": "🎉 Новый друг добавлен! +5 баллов!\nИтого: {points} ⭐",
        "top": "🏆 Топ 10 пользователей:\n\n{list}",
        "profile": "👤 Профиль\n\n🆔 ID: {id}\n👤 Имя: {name}\n🌐 Язык: {lang}\n🏆 Баллы: {points} ⭐\n📥 Загрузок: {downloads}\n👥 Приглашено: {refs}\n📅 Регистрация: {date}",
        "trim_ask": "✂️ Введите время для обрезки:\nФормат: `начало конец`\nПример: `0:30 1:00`",
        "trim_processing": "✂️ Обрезка видео...",
        "ad_set": "✅ Текст рекламы установлен!",
        "ad_del": "✅ Реклама удалена!",
        "broadcast_done": "📢 Сообщение отправлено {count} пользователям!",
        "stats": "📊 Статистика\n\n👥 Всего пользователей: {users}\n📥 Сегодня загрузок: {today}\n📅 За месяц: {month}\n🚫 Заблокировано: {banned}\n🌐 Языки:\n  🇺🇿 Узбекский: {uz}\n  🇷🇺 Русский: {ru}\n  🇹🇯 Таджикский: {tj}",
        "ban_done": "🚫 Пользователь {id} заблокирован!",
        "unban_done": "✅ Пользователь {id} разблокирован!",
        "bot_stopped": "🔴 Бот остановлен!",
        "bot_started": "🟢 Бот запущен!",
        "help": "📖 Помощь\n\n🎬 Скачать видео:\nОтправьте ссылку YouTube, TikTok или Pinterest\n\n🎵 Поиск музыки:\n/music [название] или [исполнитель]\n\n👥 Пригласить друга:\n/ref\n\n🏆 Рейтинг:\n/top\n\n👤 Профиль:\n/profile\n\n✂️ Обрезать видео:\n/trim [ссылка]\n\n❓ По любым вопросам администратор доступен 24/7: @qodircg",
    },
    "tj": {
        "start": "👋 Салом, {name}!\n\n🎬 Ман аз YouTube, TikTok ва Pinterest видео ва мусиқа зеркашӣ мекунам!\n\n📌 Истифода:\n• Пайванди YouTube/TikTok/Pinterest-ро фиристед\n• Ё номи мусиқаро нависед\n\n🏆 Холҳои шумо: {points} ⭐\n👥 Даъватшудагон: {refs}",
        "sub_required": "⚠️ Барои истифода аз бот ба канал обуна шавед!\n\n📢 Канал: {channel}\n\nПас аз обуна ✅ Санҷиданро пахш кунед.",
        "sub_check": "✅ Санҷидан",
        "sub_ok": "✅ Обуна тасдиқ шуд! Акнун пайвандро фиристед.",
        "sub_fail": "❌ Шумо ҳанӯз обуна нашудаед!\n\n📢 Ба {channel} обуна шавед.",
        "banned": "🚫 Шумо аз бот манъ шудаед.\n\nМуроҷиат: @qodircg",
        "bot_off": "🔴 Бот ҳоло кор намекунад. Баъдтар кӯшиш кунед.",
        "limit": "⚠️ Лимити рӯзонаи шумо тамом шуд!\n\n📊 Лимит: {limit} видео дар рӯз\n🔄 Лимит фардо навсозӣ мешавад.",
        "sending_link": "🔗 Пайванд тайёр мешавад...",
        "downloading": "⏳ Зеркашӣ...\n\n🔗 {url}",
        "choose_quality": "🎬 Сифатро интихоб кунед:",
        "choose_format": "🎵 Форматро интихоб кунед:",
        "size_info": "📦 Ҳаҷми тахминӣ: {size}\n⏱ Давомнокӣ: {duration}\n👁 Бинишҳо: {views}\n\n📥 Форматро интихоб кунед:",
        "done": "✅ Тайёр!\n\n📥 Зеркашӣ:\n{link}\n\n⚠️ Пайванд пас аз {minutes} дақиқа нест мешавад!\n\n🏆 +1 хол! Ҷамъ: {points} ⭐",
        "error": "😔 Бубахшед, ин видеоро зеркашӣ карда нашуд.\n\nСабаб метавонад:\n• Видео пӯшида/private\n• Пайванди нодуруст\n• Мушкили сервер\n\n🔄 Бо пайванди дигар кӯшиш кунед.",
        "music_search": "🎵 Ҷустуҷӯи мусиқа: {query}",
        "music_results": "🎵 Натиҷаҳо:",
        "no_results": "😔 Ҳеҷ чиз ёфт нашуд.",
        "ref_link": "👥 Дӯстонатонро даъват кунед!\n\n🔗 Пайванди шумо:\n{link}\n\n🏆 +5 хол барои ҳар яке!\n👥 Даъватшудагон: {count}",
        "new_ref": "🎉 Дӯсти нав илова шуд! +5 хол!\nҶамъ: {points} ⭐",
        "top": "🏆 Топ 10 корбарон:\n\n{list}",
        "profile": "👤 Профил\n\n🆔 ID: {id}\n👤 Ном: {name}\n🌐 Забон: {lang}\n🏆 Хол: {points} ⭐\n📥 Зеркашиҳо: {downloads}\n👥 Даъватшудагон: {refs}\n📅 Сана: {date}",
        "trim_ask": "✂️ Вақтро барои буридан ворид кунед:\nФормат: `оғоз анҷом`\nМисол: `0:30 1:00`",
        "trim_processing": "✂️ Видео буррида мешавад...",
        "ad_set": "✅ Матни реклама насб шуд!",
        "ad_del": "✅ Реклама нест шуд!",
        "broadcast_done": "📢 Паём ба {count} корбар фиристода шуд!",
        "stats": "📊 Омор\n\n👥 Ҷамъи корбарон: {users}\n📥 Зеркашиҳои имрӯз: {today}\n📅 Моҳона: {month}\n🚫 Манъшудагон: {banned}",
        "ban_done": "🚫 Корбари {id} манъ шуд!",
        "unban_done": "✅ Корбари {id} аз манъ озод шуд!",
        "bot_stopped": "🔴 Бот қатъ шуд!",
        "bot_started": "🟢 Бот фаъол шуд!",
        "help": "📖 Кӯмак\n\n🎬 Зеркашии видео:\nПайванди YouTube, TikTok ё Pinterest-ро фиристед\n\n🎵 Ҷустуҷӯи мусиқа:\n/music [ном]\n\n👥 Даъвати дӯст:\n/ref\n\n🏆 Рейтинг:\n/top\n\n👤 Профил:\n/profile",
    }
}

# ─── Database ────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            lang TEXT DEFAULT 'uz',
            points INTEGER DEFAULT 0,
            downloads INTEGER DEFAULT 0,
            daily_count INTEGER DEFAULT 0,
            daily_date TEXT DEFAULT '',
            refs INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            joined_date TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            date TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.executemany("INSERT OR IGNORE INTO settings VALUES (?, ?)", [
        ("bot_active", "1"),
        ("ad_text", ""),
    ])
    conn.commit()
    conn.close()


def get_user(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    row = c.fetchone()
    conn.close()
    return row


def add_user(uid, name, lang="uz", ref=0):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        INSERT OR IGNORE INTO users (id, name, lang, joined_date, referred_by)
        VALUES (?, ?, ?, ?, ?)
    """, (uid, name, lang, today, ref))
    conn.commit()
    conn.close()


def update_user(uid, **kwargs):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    for key, val in kwargs.items():
        c.execute(f"UPDATE users SET {key}=? WHERE id=?", (val, uid))
    conn.commit()
    conn.close()


def get_setting(key):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""


def set_setting(key, value):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_stats():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM downloads WHERE date LIKE ?", (f"{today}%",))
    today_dl = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM downloads WHERE date LIKE ?", (f"{month}%",))
    month_dl = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
    banned = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE lang='uz'")
    uz = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE lang='ru'")
    ru = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE lang='tj'")
    tj = c.fetchone()[0]
    conn.close()
    return users, today_dl, month_dl, banned, uz, ru, tj


def get_top():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT id, name, points FROM users ORDER BY points DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_users():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE is_banned=0")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def log_download(uid, url):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO downloads (user_id, url, date) VALUES (?, ?, ?)", (uid, url, now))
    conn.commit()
    conn.close()


# ─── Helpers ─────────────────────────────────────────────────────────────────
def t(lang, key, **kwargs):
    text = TEXTS.get(lang, TEXTS["uz"]).get(key, TEXTS["uz"].get(key, ""))
    return text.format(**kwargs) if kwargs else text


def get_lang(uid):
    user = get_user(uid)
    return user[2] if user else "uz"


def is_admin(uid):
    return uid == ADMIN_ID


def check_daily(uid):
    user = get_user(uid)
    if not user:
        return True
    today = datetime.now().strftime("%Y-%m-%d")
    if user[6] != today:
        update_user(uid, daily_count=0, daily_date=today)
        return True
    return user[5] < DAILY_LIMIT


def increment_daily(uid):
    user = get_user(uid)
    if not user:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    if user[6] != today:
        update_user(uid, daily_count=1, daily_date=today)
    else:
        update_user(uid, daily_count=user[5] + 1)


def add_points(uid, pts):
    user = get_user(uid)
    if user:
        update_user(uid, points=user[3] + pts)
        return user[3] + pts
    return pts


def format_size(bytes_val):
    if bytes_val < 1024 * 1024:
        return f"{bytes_val/1024:.1f} KB"
    return f"{bytes_val/(1024*1024):.1f} MB"


def format_duration(seconds):
    if not seconds:
        return "N/A"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


async def check_subscription(bot, uid):
    try:
        member = await bot.get_chat_member(CHANNEL, uid)
        return member.status not in ["left", "kicked"]
    except Exception:
        return False


async def shorten_url(url):
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
        logger.error(f"Shrinkme: {e}")
    return url


async def upload_catbox(path):
    try:
        async with httpx.AsyncClient() as c:
            with open(path, "rb") as f:
                r = await c.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": f},
                    timeout=300,
                )
                return r.text.strip()
    except Exception as e:
        logger.error(f"Catbox: {e}")
    return ""


def get_video_info(url):
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logger.error(f"Info error: {e}")
        return None


async def download_video(url, folder, quality="best", is_audio=False):
    os.makedirs(folder, exist_ok=True)
    if is_audio:
        opts = {
            "outtmpl": folder + "/audio.%(ext)s",
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
            "no_warnings": True,
        }
    else:
        fmt = {
            "360": "18/best[height<=360]",
            "480": "best[height<=480]",
            "720": "22/best[height<=720]",
            "1080": "best[height<=1080]",
            "best": "18/22/best",
        }.get(quality, "18/22/best")
        opts = {
            "outtmpl": folder + "/video.%(ext)s",
            "format": fmt,
            "quiet": True,
            "no_warnings": True,
        }

    loop = asyncio.get_event_loop()

    def go():
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    await loop.run_in_executor(None, go)
    files = []
    for f in os.listdir(folder):
        if f.endswith((".mp4", ".webm", ".mkv", ".mp3", ".m4a")):
            files.append(os.path.join(folder, f))
    return sorted(files)


async def search_music(query):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "default_search": "ytsearch5",
        "extract_flat": True,
    }
    try:
        loop = asyncio.get_event_loop()
        def go():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(f"ytsearch5:{query}", download=False)
        info = await loop.run_in_executor(None, go)
        return info.get("entries", [])[:5]
    except Exception as e:
        logger.error(f"Search: {e}")
        return []


# ─── Handlers ────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name or "Foydalanuvchi"

    # Ref
    ref = 0
    if context.args:
        try:
            ref = int(context.args[0])
        except Exception:
            pass

    # Add user
    if not get_user(uid):
        add_user(uid, name, ref=ref)
        # Ref bonus
        if ref and ref != uid:
            referer = get_user(ref)
            if referer:
                new_pts = add_points(ref, 5)
                update_user(ref, refs=referer[8] + 1)
                try:
                    lang_r = referer[2]
                    await context.bot.send_message(ref, t(lang_r, "new_ref", points=new_pts))
                except Exception:
                    pass
    else:
        update_user(uid, name=name)

    # Bot active?
    if get_setting("bot_active") == "0" and not is_admin(uid):
        lang = get_lang(uid)
        await update.message.reply_text(t(lang, "bot_off"))
        return

    # Banned?
    user = get_user(uid)
    if user and user[9]:
        lang = get_lang(uid)
        await update.message.reply_text(t(lang, "banned"))
        return

    # Lang selection
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="lang_tj"),
        ]
    ])
    await update.message.reply_text(
        t("uz", "choose_lang"),
        reply_markup=kb
    )


async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = q.data.split("_")[1]
    update_user(uid, lang=lang)

    # Sub check
    subbed = await check_subscription(context.bot, uid)
    if not subbed:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Kanal", url=f"https://t.me/{CHANNEL.lstrip('@')}"),
            InlineKeyboardButton(t(lang, "sub_check"), callback_data="check_sub"),
        ]])
        await q.edit_message_text(t(lang, "sub_required", channel=CHANNEL), reply_markup=kb)
        return

    user = get_user(uid)
    pts = user[3] if user else 0
    refs = user[8] if user else 0
    name = q.from_user.first_name or "Foydalanuvchi"
    await q.edit_message_text(t(lang, "start", name=name, points=pts, refs=refs))


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid)

    subbed = await check_subscription(context.bot, uid)
    if not subbed:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Kanal", url=f"https://t.me/{CHANNEL.lstrip('@')}"),
            InlineKeyboardButton(t(lang, "sub_check"), callback_data="check_sub"),
        ]])
        await q.edit_message_text(t(lang, "sub_fail", channel=CHANNEL), reply_markup=kb)
        return

    user = get_user(uid)
    pts = user[3] if user else 0
    refs = user[8] if user else 0
    name = q.from_user.first_name or ""
    await q.edit_message_text(t(lang, "start", name=name, points=pts, refs=refs))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    await update.message.reply_text(t(lang, "help"))


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    user = get_user(uid)
    if not user:
        return
    lang_names = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "tj": "🇹🇯 Тоҷикӣ"}
    await update.message.reply_text(t(lang, "profile",
        id=uid,
        name=user[1],
        lang=lang_names.get(user[2], user[2]),
        points=user[3],
        downloads=user[4],
        refs=user[8],
        date=user[10]
    ))


async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    rows = get_top()
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (rid, rname, rpts) in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} {rname} — {rpts} ⭐")
    await update.message.reply_text(t(lang, "top", list="\n".join(lines)))


async def ref_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    user = get_user(uid)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={uid}"
    refs = user[8] if user else 0
    await update.message.reply_text(t(lang, "ref_link", link=link, count=refs))


async def music_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    query = " ".join(context.args) if context.args else update.message.text.replace("/music", "").strip()
    if not query:
        await update.message.reply_text("🎵 /music [qo'shiq nomi yoki qo'shiqchi]")
        return

    msg = await update.message.reply_text(t(lang, "music_search", query=query))
    results = await search_music(query)

    if not results:
        await msg.edit_text(t(lang, "no_results"))
        return

    kb = []
    for r in results:
        title = r.get("title", "N/A")[:40]
        vid_id = r.get("id", "")
        duration = format_duration(r.get("duration"))
        kb.append([InlineKeyboardButton(
            f"🎵 {title} [{duration}]",
            callback_data=f"music_{vid_id}"
        )])

    await msg.edit_text(t(lang, "music_results"), reply_markup=InlineKeyboardMarkup(kb))


async def music_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid)
    vid_id = q.data.split("_", 1)[1]
    url = f"https://youtube.com/watch?v={vid_id}"

    await q.edit_message_text(t(lang, "downloading", url=url))

    folder = f"/tmp/music_{uid}"
    try:
        files = await download_video(url, folder, is_audio=True)
        if not files:
            await q.edit_message_text(t(lang, "error"))
            return

        upload_url = await upload_catbox(files[0])
        if not upload_url:
            await q.edit_message_text(t(lang, "error"))
            return

        short = await shorten_url(upload_url)
        pts = add_points(uid, 1)
        ad = get_setting("ad_text")
        text = t(lang, "done", link=short, minutes=10, points=pts)
        if ad:
            text += f"\n\n📢 {ad}"

        msg = await q.edit_message_text(text)
        log_download(uid, url)
        increment_daily(uid)

        # 10 daqiqadan keyin o'chir
        asyncio.create_task(delete_after(context.bot, msg.chat_id, msg.message_id))

    except Exception as e:
        logger.exception(e)
        await q.edit_message_text(t(lang, "error"))
    finally:
        import shutil
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)


async def delete_after(bot, chat_id, msg_id):
    await asyncio.sleep(DELETE_AFTER)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    url = update.message.text.strip()

    # Checks
    if get_setting("bot_active") == "0" and not is_admin(uid):
        await update.message.reply_text(t(lang, "bot_off"))
        return

    user = get_user(uid)
    if not user:
        await start(update, context)
        return

    if user[9]:
        await update.message.reply_text(t(lang, "banned"))
        return

    subbed = await check_subscription(context.bot, uid)
    if not subbed:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Kanal", url=f"https://t.me/{CHANNEL.lstrip('@')}"),
            InlineKeyboardButton(t(lang, "sub_check"), callback_data="check_sub"),
        ]])
        await update.message.reply_text(t(lang, "sub_required", channel=CHANNEL), reply_markup=kb)
        return

    if not check_daily(uid) and not is_admin(uid):
        await update.message.reply_text(t(lang, "limit", limit=DAILY_LIMIT))
        return

    # Get info
    msg = await update.message.reply_text(t(lang, "downloading", url=url))
    info = get_video_info(url)

    if not info:
        await msg.edit_text(t(lang, "error"))
        return

    title = info.get("title", "Video")[:50]
    duration = format_duration(info.get("duration"))
    views = f"{info.get('view_count', 0):,}" if info.get("view_count") else "N/A"
    filesize = info.get("filesize") or info.get("filesize_approx") or 0
    size = format_size(filesize) if filesize else "N/A"

    context.user_data["download_url"] = url
    context.user_data["video_title"] = title

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 MP3", callback_data="dl_mp3"),
            InlineKeyboardButton("📱 360p", callback_data="dl_360"),
        ],
        [
            InlineKeyboardButton("📺 480p", callback_data="dl_480"),
            InlineKeyboardButton("🎬 720p", callback_data="dl_720"),
        ],
        [InlineKeyboardButton("🔥 1080p", callback_data="dl_1080")],
    ])

    await msg.edit_text(
        f"🎬 {title}\n\n" + t(lang, "size_info", size=size, duration=duration, views=views),
        reply_markup=kb
    )


async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid)
    action = q.data.split("_")[1]

    url = context.user_data.get("download_url")
    if not url:
        await q.edit_message_text(t(lang, "error"))
        return

    is_audio = action == "mp3"
    quality = action if not is_audio else "best"

    await q.edit_message_text(t(lang, "downloading", url=url))

    folder = f"/tmp/dl_{uid}"
    try:
        files = await download_video(url, folder, quality=quality, is_audio=is_audio)
        if not files:
            await q.edit_message_text(t(lang, "error"))
            return

        upload_url = await upload_catbox(files[0])
        if not upload_url:
            await q.edit_message_text(t(lang, "error"))
            return

        short = await shorten_url(upload_url)
        pts = add_points(uid, 1)
        log_download(uid, url)
        increment_daily(uid)
        update_user(uid, downloads=(get_user(uid)[4] or 0) + 1)

        ad = get_setting("ad_text")
        text = t(lang, "done", link=short, minutes=10, points=pts)
        if ad:
            text += f"\n\n📢 {ad}"

        msg = await q.edit_message_text(text)
        asyncio.create_task(delete_after(context.bot, msg.chat_id, msg.message_id))

    except Exception as e:
        logger.exception(e)
        await q.edit_message_text(t(lang, "error"))
    finally:
        import shutil
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)


# ─── Admin commands ───────────────────────────────────────────────────────────
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    users, today, month, banned, uz, ru, tj = get_stats()
    await update.message.reply_text(t("uz", "stats",
        users=users, today=today, month=month,
        banned=banned, uz=uz, ru=ru, tj=tj
    ))


async def setreklama_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = " ".join(context.args)
    set_setting("ad_text", text)
    await update.message.reply_text(t("uz", "ad_set"))


async def delreklama_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    set_setting("ad_text", "")
    await update.message.reply_text(t("uz", "ad_del"))


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("❌ /broadcast [matn]")
        return
    text = " ".join(context.args)
    users = get_all_users()
    count = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, text)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await update.message.reply_text(t("uz", "broadcast_done", count=count))


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("❌ /ban [user_id]")
        return
    try:
        target = int(context.args[0])
        update_user(target, is_banned=1)
        await update.message.reply_text(t("uz", "ban_done", id=target))
    except Exception:
        await update.message.reply_text("❌ Xatolik")


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("❌ /unban [user_id]")
        return
    try:
        target = int(context.args[0])
        update_user(target, is_banned=0)
        await update.message.reply_text(t("uz", "unban_done", id=target))
    except Exception:
        await update.message.reply_text("❌ Xatolik")


async def stopbot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    set_setting("bot_active", "0")
    await update.message.reply_text(t("uz", "bot_stopped"))


async def startbot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    set_setting("bot_active", "1")
    await update.message.reply_text(t("uz", "bot_started"))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    text = update.message.text.strip()

    # URL check
    url_patterns = ["youtube.com", "youtu.be", "tiktok.com", "pinterest.com", "pin.it"]
    if any(p in text.lower() for p in url_patterns):
        await handle_url(update, context)
        return

    # Music search
    await music_cmd(update, context)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("ref", ref_cmd))
    app.add_handler(CommandHandler("music", music_cmd))

    # Admin commands
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("setreklama", setreklama_cmd))
    app.add_handler(CommandHandler("delreklama", delreklama_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("stopbot", stopbot_cmd))
    app.add_handler(CommandHandler("startbot", startbot_cmd))

    # Callbacks
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(download_callback, pattern="^dl_"))
    app.add_handler(CallbackQueryHandler(music_callback, pattern="^music_"))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("✅ Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
