import os
import html
import logging
from collections import defaultdict

from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Память диалога в RAM: {user_id: [{"role": "...", "content": "..."}]}
user_memory = defaultdict(list)

SYSTEM_PROMPT = """
Ты полезный AI-помощник в Telegram.
Отвечай кратко, понятно и по делу.
Если пользователь пишет по-русски — отвечай по-русски.
Если просит код — давай рабочий пример.
Если вопрос неясен — сначала уточни недостающие детали.
"""

MAX_HISTORY_MESSAGES = 12
TELEGRAM_TEXT_LIMIT = 4000


def build_conversation_text(history: list[dict], user_message: str) -> str:
    """
    Собирает историю в один текстовый prompt.
    """
    lines = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = "User" if item["role"] == "user" else "Assistant"
        lines.append(f"{role}: {item['content']}")
    lines.append(f"User: {user_message}")
    lines.append("Assistant:")
    return "\n".join(lines)


def split_text(text: str, chunk_size: int = TELEGRAM_TEXT_LIMIT):
    """
    Делит длинный текст на части для Telegram.
    """
    parts = []
    while len(text) > chunk_size:
        split_at = text.rfind("\n", 0, chunk_size)
        if split_at == -1:
            split_at = chunk_size
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        parts.append(text)
    return parts


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! Я AI Telegram Bot.\n\n"
        "Что умею:\n"
        "• отвечаю на вопросы\n"
        "• помогаю с кодом\n"
        "• объясняю тексты\n"
        "• генерирую идеи\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/help — помощь\n"
        "/new — очистить историю диалога\n\n"
        "Просто напиши сообщение."
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Примеры:\n"
        "• Напиши продающий текст для магазина одежды\n"
        "• Объясни, что делает этот Python-код\n"
        "• Составь план изучения английского на 30 дней\n"
        "• Напиши Telegram-бота на aiogram\n\n"
        "Если хочешь начать новый диалог без старого контекста — используй /new"
    )
    await update.message.reply_text(text)


async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_memory[user_id] = []
    await update.message.reply_text("История диалога очищена ✅")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    if not user_text:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    history = user_memory[user_id]
    prompt_text = build_conversation_text(history, user_text)

    try:
        response = await client.responses.create(
            model=OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            input=prompt_text,
        )

        answer = (response.output_text or "").strip()

        if not answer:
            answer = "Не удалось получить ответ от модели. Попробуй ещё раз."

        # Сохраняем в память
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": answer})
        user_memory[user_id] = history[-MAX_HISTORY_MESSAGES:]

        for part in split_text(answer):
            await update.message.reply_text(part)

    except Exception as e:
        logger.exception("OpenAI request error: %s", e)
        safe_error = html.escape(str(e))
        await update.message.reply_text(
            f"Ошибка при обращении к AI-сервису:\n<code>{safe_error}</code>",
            parse_mode="HTML"
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram error:", exc_info=context.error)


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.add_error_handler(error_handler)

    print("AI Telegram bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
