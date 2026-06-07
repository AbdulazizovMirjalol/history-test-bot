from __future__ import annotations

import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

from database import (
    connect,
    get_next_question,
    get_options,
    get_stats,
    init_db,
    record_answer,
    reset_progress,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "questions.db"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and add your BotFather token.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def db():
    conn = connect(DATABASE_PATH)
    init_db(conn)
    return conn


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Test ishlash", callback_data="mode:study")],
            [InlineKeyboardButton(text="🔥 Qiyin savollar", callback_data="mode:hard")],
            [InlineKeyboardButton(text="📊 Statistika", callback_data="mode:stats")],
        ]
    )


def question_keyboard(question_id: int, correct_answer: str, options: list[str], hard_only: bool) -> InlineKeyboardMarkup:
    rows = []
    for option in options:
        is_correct = "1" if option == correct_answer else "0"
        hard_flag = "1" if hard_only else "0"
        rows.append(
            [
                InlineKeyboardButton(
                    text=option,
                    callback_data=f"ans:{question_id}:{is_correct}:{hard_flag}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🏠 Menyu", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_question(chat_id: int, user_id: int, hard_only: bool = False) -> None:
    conn = db()
    row = get_next_question(conn, user_id=user_id, hard_only=hard_only)
    conn.close()

    if row is None:
        text = "Hozircha bu rejimda savol topilmadi. Avval /study orqali bir nechta test ishlang."
        await bot.send_message(chat_id, text, reply_markup=main_menu())
        return

    options = get_options(row)
    prefix = "🔥 Qiyin savol" if hard_only else "📚 Savol"
    text = f"{prefix} #{row['source_number']}\n\n{row['question']}"
    await bot.send_message(
        chat_id,
        text,
        reply_markup=question_keyboard(row["id"], row["correct_answer"], options, hard_only),
    )


async def send_stats(chat_id: int, user_id: int) -> None:
    conn = db()
    stats = get_stats(conn, user_id)
    conn.close()

    text = (
        "📊 Sizning natijangiz:\n\n"
        f"Jami savollar: {stats['total']}\n"
        f"Ko‘rilgan savollar: {stats['seen']}\n"
        f"Yangi savollar: {stats['new']}\n"
        f"Bugun qaytariladiganlar: {stats['due']}\n"
        f"Qiyin savollar: {stats['hard']}\n"
        f"Yodlangan savollar: {stats['mastered']}"
    )
    await bot.send_message(chat_id, text, reply_markup=main_menu())


@dp.message(Command("start"))
async def start(message: Message) -> None:
    text = (
        "Assalomu alaykum! Men tarix testlarini yodlashga yordam beraman.\n\n"
        "To‘g‘ri javob bersangiz savol kamroq chiqadi, xato qilsangiz qayta-qayta takrorlanadi."
    )
    await message.answer(text, reply_markup=main_menu())


@dp.message(Command("study"))
async def study(message: Message) -> None:
    await send_question(message.chat.id, message.from_user.id, hard_only=False)


@dp.message(Command("hard"))
async def hard(message: Message) -> None:
    await send_question(message.chat.id, message.from_user.id, hard_only=True)


@dp.message(Command("stats"))
async def stats(message: Message) -> None:
    await send_stats(message.chat.id, message.from_user.id)


@dp.message(Command("reset"))
async def reset(message: Message) -> None:
    conn = db()
    reset_progress(conn, message.from_user.id)
    conn.close()
    await message.answer("Progress tozalandi. Qaytadan boshlashingiz mumkin.", reply_markup=main_menu())


@dp.callback_query(F.data == "menu")
async def menu(callback: CallbackQuery) -> None:
    await callback.message.answer("Menyu:", reply_markup=main_menu())
    await callback.answer()


@dp.callback_query(F.data == "mode:study")
async def mode_study(callback: CallbackQuery) -> None:
    await send_question(callback.message.chat.id, callback.from_user.id, hard_only=False)
    await callback.answer()


@dp.callback_query(F.data == "mode:hard")
async def mode_hard(callback: CallbackQuery) -> None:
    await send_question(callback.message.chat.id, callback.from_user.id, hard_only=True)
    await callback.answer()


@dp.callback_query(F.data == "mode:stats")
async def mode_stats(callback: CallbackQuery) -> None:
    await send_stats(callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@dp.callback_query(F.data.startswith("ans:"))
async def answer(callback: CallbackQuery) -> None:
    _, question_id_raw, is_correct_raw, hard_flag_raw = callback.data.split(":")
    question_id = int(question_id_raw)
    is_correct = is_correct_raw == "1"
    hard_only = hard_flag_raw == "1"

    conn = db()
    row = conn.execute("SELECT correct_answer FROM questions WHERE id = ?", (question_id,)).fetchone()
    record_answer(conn, callback.from_user.id, question_id, is_correct)
    conn.close()

    if is_correct:
        await callback.message.answer("✅ To‘g‘ri! Zo‘r, keyingi savolga o‘tamiz.")
    else:
        correct = row["correct_answer"] if row else "Noma’lum"
        await callback.message.answer(f"❌ Xato. To‘g‘ri javob: {correct}\nBu savol yana qaytariladi.")

    await callback.answer()
    await send_question(callback.message.chat.id, callback.from_user.id, hard_only=hard_only)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
