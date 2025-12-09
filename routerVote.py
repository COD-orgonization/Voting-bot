# routerVote.py
from aiogram import types, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import F

from DataBase.mainDB import UserDB

# Инициализация базы данных
db = UserDB()

router = Router()

@router.message(F.text == "🗳️ Проголосовать")
async def vote_start(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, зарегистрирован ли пользователь
    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    # Проверяем, голосовал ли уже пользователь
    if db.has_user_voted(user_id):
        await message.answer("✅ Вы уже проголосовали!")
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
            callback_data=f"show_user_{user_data['id']}"
        )])
    
    vote_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Выберите пользователя для просмотра:", reply_markup=vote_keyboard)

@router.callback_query(F.data.startswith("show_user_"))
async def show_user_details(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    # Получаем информацию о пользователе
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    # Отправляем информацию о пользователе с фото
    caption = f"👤 <b>{user['fio']}</b>\n\n"
    caption += f"📝 <b>О себе:</b>\n{user['description']}\n\n"
    caption += f"❤️ Голосов: {user['vote_count']}"
    
    # Создаем клавиатуру с кнопкой для голосования
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Проголосовать за этого пользователя", callback_data=f"vote_{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="back_to_list")]
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

@router.callback_query(F.data == "back_to_list")
async def back_to_user_list(callback: types.CallbackQuery):
    voter_id = callback.from_user.id
    
    # Получаем список пользователей для голосования
    users_for_voting = db.get_users_for_voting(exclude_id=voter_id)
    
    if not users_for_voting:
        await callback.answer("❌ Пока нет других участников для голосования!", show_alert=True)
        return
    
    # Создаем клавиатуру для голосования
    keyboard = []
    for user_data in users_for_voting:
        keyboard.append([InlineKeyboardButton(
            text=f"👤 {user_data['fio']}", 
            callback_data=f"show_user_{user_data['id']}"
        )])
    
    vote_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.delete()  # Удаляем предыдущее сообщение
    await callback.message.answer("Выберите пользователя для просмотра:", reply_markup=vote_keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: types.CallbackQuery):
    voter_id = callback.from_user.id
    target_id = int(callback.data.split("_")[1])
    
    # Обрабатываем голосование
    if db.process_vote(voter_id, target_id):
        target_user = db.get_user(target_id)
        
        # Обновляем сообщение с результатом
        caption = f"✅ Вы успешно проголосовали за <b>{target_user['fio']}</b>!\n\n"
        caption += f"👤 <b>{target_user['fio']}</b>\n\n"
        caption += f"📝 <b>О себе:</b>\n{target_user['description']}\n\n"
        caption += f"❤️ Голосов: {target_user['vote_count']}"
        
        await callback.message.edit_caption(
            caption=caption,
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.answer("❌ Не удалось проголосовать. Возможно, вы уже голосовали.", show_alert=True)