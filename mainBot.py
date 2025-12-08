# import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import F

from DataBase.confing import TOKEN
from routerRegistration import router
from DataBase.mainDB import UserDB
# logging.basicConfig(level=logging.INFO)

bot = Bot(token= TOKEN)
dp = Dispatcher()
dp.include_router(router)
db = UserDB()

# Меню
menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Регистрация"), KeyboardButton(text="🗳️ Проголосовать")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Добро пожаловать! Выберите действие:", reply_markup=menu_keyboard)

# Голосование
@dp.message(F.text == "🗳️ Проголосовать")
async def vote_start(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, зарегистрирован ли пользователь
    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    # Проверяем, голосовал ли уже пользователь
    if db.has_user_voted(user_id):
        await message.answer("❌ Вы уже проголосовали!")
        return
    
    # Получаем список пользователей для голосования
    users_for_voting = db.get_users_for_voting(exclude_id=user_id)
    
    if not users_for_voting:
        await message.answer("❌ Пока нет других участников для голосования!")
        return
    
    # Создаем клавиатуру для голосования
    keyboard = []
    for user_data in users_for_voting:
        keyboard.append([InlineKeyboardButton(
            text=f"👤 {user_data['fio']}", 
            callback_data=f"vote_{user_data['id']}"
        )])
    
    vote_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Выберите пользователя для голосования:", reply_markup=vote_keyboard)

@dp.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: types.CallbackQuery):
    voter_id = callback.from_user.id
    target_id = int(callback.data.split("_")[1])
    
    # Обрабатываем голосование
    if db.process_vote(voter_id, target_id):
        target_user = db.get_user(target_id)
        await callback.message.answer(f"✅ Вы успешно проголосовали за {target_user['fio']}!")
        await callback.answer()
    else:
        await callback.answer("❌ Не удалось проголосовать. Возможно, вы уже голосовали.", show_alert=True)

# Статистика
@dp.message(Command("get_state"))
async def show_statistics(message: types.Message):
    # Получаем всех пользователей отсортированных по количеству голосов
    users = db.get_all_users()
    users_sorted = sorted(users, key=lambda x: x['vote_count'], reverse=True)
    
    if not users_sorted:
        await message.answer("❌ Нет данных для статистики.")
        return
    
    # Формируем сообщение со статистикой
    stats_text = "📊 Текущая статистика:\n\n"
    for i, user in enumerate(users_sorted, 1):
        stats_text += f"{i}. {user['fio']}: {user['vote_count']} голосов\n"
    
    await message.answer(stats_text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())