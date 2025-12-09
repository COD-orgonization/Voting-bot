from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import F

from DataBase.confing import TOKEN
from routerRegistration import router as routerReg
from routerVote import router as routerVoit
from DataBase.mainDB import UserDB

bot = Bot(token= TOKEN)
dp = Dispatcher()
dp.include_router(routerReg)
dp.include_router(routerVoit)
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

# Статистика
@dp.message(Command("admin_comand_get_state"))
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

@dp.message(Command("reset_votes"))
async def cmd_reset_votes(message: types.Message):
    db.reset_votes()
    await message.answer("✅ Все голосы сброшены!")

@dp.message(Command("start_voting"))
async def start_voting(message: types.Message):
    """Команда для запуска голосования"""
    try:
        if db.set_voting_enabled(True):
            await message.answer("✅ Голосование началось! Все пользователи могут голосовать.")
            
            # Рассылка всем пользователям о начале голосования
            users = db.get_all_users()
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user['id'],
                        text="🎉 Голосование началось! Нажмите '🗳️ Проголосовать' в меню, чтобы принять участие."
                    )
                except:
                    pass  # Игнорируем ошибки отправки
        else:
            await message.answer("❌ Ошибка при запуске голосования.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("stop_voting"))
async def stop_voting(message: types.Message):
    """Команда для завершения голосования"""
    try:
        if db.set_voting_enabled(False):
            await message.answer("✅ Голосование завершено!")
            
            users = db.get_all_users()
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user['id'],
                        text="⏸️ Голосование завершено!"
                    )
                except:
                    pass  # Игнорируем ошибки отправки
            
            # Показываем финальную статистику
            await show_statistics(message)
        else:
            await message.answer("❌ Ошибка при завершении голосования.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())