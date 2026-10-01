import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode

# === НАСТРОЙКИ ===
BOT_TOKEN = "8157847394:AAFK07sbsYodV2ufgSnm6dMxuXHoK622fNA"
CHANNEL_ID = -1003139666603
ADMIN_IDS = [8760282359, 8864286623]

# === ИНИЦИАЛИЗАЦИЯ ===
logging.basicConfig(level=logging.INFO)
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

pending_posts = {}

# === ПРИЁМ СООБЩЕНИЙ ОТ ПОДПИСЧИКОВ ===
@dp.message(F.chat.type == "private")
async def handle_submission(message: types.Message):
    if message.text and message.text.startswith("/"):
        return

    user_id = message.from_user.id
    username = message.from_user.username or "без_юзернейма"
    full_name = message.from_user.full_name

    post_text = message.text or message.caption or "[медиа без текста]"
    anon_post = f"<b>Анонимная подслушка:</b>\n\n{post_text}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{message.message_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{message.message_id}")
        ]
    ])

    pending_posts[message.message_id] = {
        "author_id": user_id,
        "text": post_text,
        "media": message.photo[-1].file_id if message.photo else None
    }

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=anon_post,
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Не смог отправить админу {admin_id}: {e}")

    await message.answer("Твоё сообщение отправлено на модерацию. Если одобрят — опубликуют анонимно.")

# === ОБРАБОТКА КНОПОК ===
@dp.callback_query(F.data.startswith("approve:"))
async def approve_post(callback: CallbackQuery):
    if callback.from_user.id not in [8760282359, 8864286623]:
        await callback.answer("Ты не админ, иди нахуй.")
        return

    msg_id = int(callback.data.split(":")[1])
    post_data = pending_posts.get(msg_id)

    if not post_data:
        await callback.answer("Пост уже обработан или утерян.")
        return

    # Публикуем в канал
    try:
        if post_data["media"]:
            await bot.send_photo(
                chat_id=-1003139666603,
                photo=post_data["media"],
                caption=f"<blockquote>{post_data['text']}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_message(
                chat_id=-1003139666603,
                text=f"<blockquote>{post_data['text']}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        await callback.message.edit_text(f"{callback.message.text}\n\n✅ <b>Опубликовано</b>")
        await bot.send_message(post_data["author_id"], "Твой пост опубликован анонимно.")
    except Exception as e:
        await callback.message.edit_text(f"{callback.message.text}\n\n❌ <b>Ошибка публикации:</b> {e}")

    del pending_posts[msg_id]
    await callback.answer()

@dp.callback_query(F.data.startswith("reject:"))
async def reject_post(callback: CallbackQuery):
    if callback.from_user.id not in [8760282359, 8864286623]:
        await callback.answer("Ты не админ, иди нахуй.")
        return

    msg_id = int(callback.data.split(":")[1])
    post_data = pending_posts.get(msg_id)

    if not post_data:
        await callback.answer("Пост уже обработан.")
        return

    await callback.message.edit_text(f"{callback.message.text}\n\n❌ <b>Отклонено</b>")
    await bot.send_message(post_data["author_id"], "Твой пост отклонён модератором.")
    del pending_posts[msg_id]
    await callback.answer()

# === ЗАПУСК ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())