from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import F

from DataBase.confing import TOKEN
from routerRegistration import router as routerReg
from routerVote import router as routerVoit
from DataBase.mainDB import db

bot = Bot(token= TOKEN)
dp = Dispatcher()
dp.include_router(routerReg)
dp.include_router(routerVoit)

# Функция для создания динамического меню
async def create_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает меню в зависимости от состояния голосования"""
    is_voting_enabled = db.is_voting_enabled()
    
    keyboard_buttons = [
        [KeyboardButton(text="📝 Регистрация")]
    ]
    
    if is_voting_enabled:
        # Если голосование активно - показываем кнопку голосования
        keyboard_buttons.append([KeyboardButton(text="🗳️ Проголосовать")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    menu_keyboard = await create_menu_keyboard()
    db.add_user(message.from_user.id)

    welcome_text = """👋 Добро пожаловать в голосование за звание принца и принцессы бала!:
        <b>📋 Основные функции бота:</b>
        1. 📝 Пройдите регистрацию, чтобы участвовать в конкурсе за звание принца или принцессы балл
        2. 🗳️ Голосуйте за участников, когда начнется голосование
        3. 🔄 Используйте /reset_my_votes чтобы изменить свой выбор

        Выберите действие из меню!"""
    
    await message.answer(welcome_text, reply_markup=menu_keyboard, parse_mode="HTML")

# Удаление участника
@dp.message(Command("admin_comand_delete_user"))
async def delete_user_start(message: types.Message):
    """Начало процесса удаления пользователя"""
    # Получаем список всех пользователей
    users = db.get_all_users()
    
    if not users:
        await message.answer("❌ Нет пользователей для удаления.")
        return
    
    # Создаем инлайн-клавиатуру со списком пользователей
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = []
    for user_data in users:
        gender_icon = "👨" if user_data['gender'] else "👩"
        keyboard.append([InlineKeyboardButton(
            text=f"{gender_icon} {user_data['fio']}",
            callback_data=f"delete_show_user_{user_data['id']}"
        )])
    
    delete_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Выберите пользователя для удаления:", reply_markup=delete_keyboard)

@dp.callback_query(F.data.startswith("delete_show_user_"))
async def show_user_for_deletion(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[3])
    
    # Получаем информацию о пользователе
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    # Определяем иконку в зависимости от пола
    gender_icon = "👨" if user['gender'] else "👩"
    
    # Отправляем информацию о пользователе с фото
    caption = f"{gender_icon} <b>{user['fio']}</b>\n\n"
    caption += f"📝 <b>О себе:</b>\n{user['description']}\n\n"
    caption += f"❤️ Голосов: {user['vote_count']}"
    
    # Создаем клавиатуру с кнопкой для удаления
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Удалить пользователя", callback_data=f"delete_confirm_{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="delete_back_to_list")]
    ])
    
    # Отправляем фото с информацией
    await callback.message.delete()  # Удаляем предыдущее сообщение
    await callback.message.answer_photo(
        photo=user['photo_id'],
        caption=caption,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_confirm_"))
async def confirm_user_deletion(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    # Получаем информацию о пользователе перед удалением
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    # Находим всех, кто голосовал за удаляемого пользователя
    db.cursor.execute('SELECT id FROM users WHERE from_voice_prince = ? OR from_voice_princess = ?', (user_id, user_id))
    voters_result = db.cursor.fetchall()
    voters_ids = [voter[0] for voter in voters_result] if voters_result else []

    # Удаляем пользователя
    if db.delete_user(user_id):
        # Уведомляем удаляемого пользователя
        try:
            await bot.send_message(
                chat_id=user_id,
                text="❌ Ваш аккаунт был удален администратором из системы голосования."
            )
        except:
            pass  # Игнорируем если не удалось отправить
        
        # Уведомляем тех, кто голосовал за удаляемого пользователя
        for voter_id in voters_ids:
            try:
                await bot.send_message(
                    chat_id=voter_id,
                    text=f"⚠️ Пользователь <b>{user['fio']}</b>, за которого вы голосовали, был удален из системы.\n\n"
                         f"Ваш голос был аннулирован. Вы можете проголосовать заново, если голосование еще активно.",
                    parse_mode="HTML"
                )
            except:
                pass  # Игнорируем ошибки отправки
        
        # Обновляем сообщение с результатом
        caption = f"✅ Пользователь <b>{user['fio']}</b> успешно удален!\n\n"
        
        await callback.message.edit_caption(
            caption=caption,
            parse_mode="HTML"
        )
        await callback.answer("✅ Пользователь удален!", show_alert=True)
    else:
        await callback.answer("❌ Не удалось удалить пользователя.", show_alert=True)

@dp.callback_query(F.data == "delete_back_to_list")
async def back_to_delete_list(callback: types.CallbackQuery):
    # Получаем список всех пользователей
    users = db.get_all_users()
    
    if not users:
        await callback.message.edit_text("❌ Нет пользователей для удаления.")
        await callback.answer()
        return
    
    # Создаем инлайн-клавиатуру со списком пользователей
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = []
    for user_data in users:
        gender_icon = "👨" if user_data['gender'] else "👩"
        keyboard.append([InlineKeyboardButton(
            text=f"{gender_icon} {user_data['fio']}",
            callback_data=f"delete_show_user_{user_data['id']}"
        )])
    
    delete_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.delete()
    await callback.message.answer("Выберите пользователя для удаления:", reply_markup=delete_keyboard)
    await callback.answer()


# Статистика
@dp.message(Command("admin_comand_get_state"))
async def show_statistics(message: types.Message):
    # Получаем всех пользователей
    users = db.get_all_users()
    
    if not users:
        await message.answer("❌ Нет данных для статистики.")
        return
    
    # Разделяем пользователей на принцев и принцесс
    princes = [user for user in users if user['gender']]  # True = мужчины
    princesses = [user for user in users if not user['gender']]  # False = женщины
    
    # Сортируем по количеству голосов (по убыванию)
    princes_sorted = sorted(princes, key=lambda x: x['vote_count'], reverse=True)
    princesses_sorted = sorted(princesses, key=lambda x: x['vote_count'], reverse=True)
    
    # Формируем сообщение со статистикой
    stats_text = "👑 <b>СТАТИСТИКА ПО ПРИНЦАМ (МУЖЧИНЫ)</b>\n\n"
    
    if princes_sorted:
        for i, prince in enumerate(princes_sorted, 1):
            crown = "👑" if i == 1 and prince['vote_count'] > 0 else "👤"
            stats_text += f"{i}. {crown} <b>{prince['fio']}</b>: {prince['vote_count']} голосов\n"
    else:
        stats_text += "❌ Нет зарегистрированных принцев\n"
    
    stats_text += "\n👸 <b>СТАТИСТИКА ПО ПРИНЦЕССАМ (ДЕВУШКИ)</b>\n\n"
    
    if princesses_sorted:
        for i, princess in enumerate(princesses_sorted, 1):
            crown = "👸" if i == 1 and princess['vote_count'] > 0 else "👤"
            stats_text += f"{i}. {crown} <b>{princess['fio']}</b>: {princess['vote_count']} голосов\n"
    else:
        stats_text += "❌ Нет зарегистрированных принцесс\n"
    
    # Добавляем общую информацию
    total_princes = len(princes_sorted)
    total_princesses = len(princesses_sorted)
    
    stats_text += f"\n📊 <b>ОБЩАЯ СТАТИСТИКА:</b>\n"
    stats_text += f"👑 Принцев: {total_princes}\n"
    stats_text += f"👸 Принцесс: {total_princesses}\n"
    stats_text += f"👥 Всего участников: {total_princes + total_princesses}\n"
    
    await message.answer(stats_text, parse_mode="HTML")

@dp.message(Command("admin_comand_reset_votes"))
async def cmd_reset_votes(message: types.Message):
    db.reset_votes()
    await message.answer("✅ Все голосы сброшены!")


# Команды голосования
@dp.message(Command("admin_comand_start_voting"))
async def start_voting(message: types.Message):
    """Команда для запуска голосования"""
    try:
        if db.set_voting_enabled(True):
            await message.answer("✅ Голосование началось! Все пользователи могут голосовать.")
            
            # Рассылка всем пользователям о начале голосования
            users = db.get_all_users()
            for user in users:
                try:
                    menu_keyboard = await create_menu_keyboard()
                    await bot.send_message(
                        chat_id=user['id'],
                        text="🎉 Голосование началось! Нажмите '🗳️ Проголосовать' в меню, чтобы принять участие.",
                        reply_markup=menu_keyboard
                    )
                except:
                    pass  # Игнорируем ошибки отправки
        else:
            await message.answer("❌ Ошибка при запуске голосования.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("admin_comand_stop_voting"))
async def stop_voting(message: types.Message):
    """Команда для завершения голосования"""
    try:
        if db.set_voting_enabled(False):
            await message.answer("✅ Голосование завершено!")
            
            # Рассылка всем пользователям о завершении голосования
            users = db.get_all_users()
            for user in users:
                try:
                    menu_keyboard = await create_menu_keyboard()
                    await bot.send_message(
                        chat_id=user['id'],
                        text="⏸️ Голосование завершено!",
                        reply_markup=menu_keyboard
                    )
                except:
                    pass  # Игнорируем ошибки отправки
            
            # Показываем финальную статистику
            await show_statistics(message)
        else:
            await message.answer("❌ Ошибка при завершении голосования.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")



# Пользовательские команды
@dp.message(Command("reset_my_votes"))
async def reset_my_votes(message: types.Message):
    """Сбрасывает голоса текущего пользователя"""
    db.reset_user_votes(message.from_user.id)
    await message.answer("✅ Ваши голоса успешно сброшены!")

@dp.message(Command("delete_my_account"))
async def delete_my_account(message: types.Message):
    """Удаление текущего пользователя"""
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if db.delete_user(user_id):
        db.cursor.execute('SELECT id FROM users WHERE from_voice_prince = ? OR from_voice_princess = ?', (user_id, user_id))
        voters_result = db.cursor.fetchall()
        voters_ids = [voter[0] for voter in voters_result] if voters_result else []

        for voter_id in voters_ids:
            try:
                await bot.send_message(
                    chat_id=voter_id,
                    text=f"⚠️ Пользователь <b>{user['fio']}</b>, за которого вы голосовали, был удален из системы.\n\n"
                         f"Ваш голос был аннулирован. Вы можете проголосовать заново, если голосование еще активно.",
                    parse_mode="HTML"
                )
            except:
                pass  # Игнорируем ошибки отправки

        await message.answer("✅ Ваш акаунт успешно удалён!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())