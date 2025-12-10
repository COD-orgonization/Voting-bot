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
    
    # Получаем статус голосований пользователя
    has_voted_for_prince = db.has_user_voted(user_id, vote_for_prince=True)
    has_voted_for_princess = db.has_user_voted(user_id, vote_for_prince=False)
    
    # Создаем клавиатуру с учетом статуса голосований
    keyboard_buttons = []
    
    if has_voted_for_prince and has_voted_for_princess:
        # Пользователь уже проголосовал за обоих
        await message.answer("✅ Вы уже проголосовали за принца и принцессу!")
        
        # Показываем результаты голосований
        voted_prince_id = user.get('from_voice_prince')
        voted_princess_id = user.get('from_voice_princess')
        
        results_text = "📊 Ваши голоса:\n\n"
        
        if voted_prince_id:
            voted_prince = db.get_user(voted_prince_id)
            if voted_prince:
                results_text += f"👑 За принца: {voted_prince['fio']}\n"
        
        if voted_princess_id:
            voted_princess = db.get_user(voted_princess_id)
            if voted_princess:
                results_text += f"👸 За принцессу: {voted_princess['fio']}"
        
        await message.answer(results_text)
        return
    
    # Добавляем кнопки для голосования
    if not has_voted_for_prince:
        keyboard_buttons.append([InlineKeyboardButton(text="👑 За принцев (Мужчины)", callback_data="vote_prince")])
    
    if not has_voted_for_princess:
        keyboard_buttons.append([InlineKeyboardButton(text="👸 За принцесс (Девушки)", callback_data="vote_princess")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    status_text = "Выберите за кого хотите проголосовать:\n\n"
    status_text += f"👑 Голос за принца: {'✅ Проголосовано' if has_voted_for_prince else '❌ Не голосовал'}\n"
    status_text += f"👸 Голос за принцессу: {'✅ Проголосовано' if has_voted_for_princess else '❌ Не голосовал'}"
    
    await message.answer(status_text, reply_markup=keyboard)

@router.callback_query(F.data == "back_to_voting_menu")
async def back_to_voting_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Получаем статус голосований пользователя
    has_voted_for_prince = db.has_user_voted(user_id, vote_for_prince=True)
    has_voted_for_princess = db.has_user_voted(user_id, vote_for_prince=False)
    
    # Создаем клавиатуру с учетом статуса голосований
    keyboard_buttons = []
    
    if not has_voted_for_prince:
        keyboard_buttons.append([InlineKeyboardButton(text="👑 За принцев (Мужчины)", callback_data="vote_prince")])
    
    if not has_voted_for_princess:
        keyboard_buttons.append([InlineKeyboardButton(text="👸 За принцесс (Девушки)", callback_data="vote_princess")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    status_text = "Выберите за кого хотите проголосовать:\n\n"
    status_text += f"👑 Голос за принца: {'✅ Проголосовано' if has_voted_for_prince else '❌ Не голосовал'}\n"
    status_text += f"👸 Голос за принцессу: {'✅ Проголосовано' if has_voted_for_princess else '❌ Не голосовал'}"
    
    await callback.message.delete()
    await callback.message.answer(status_text, reply_markup=keyboard)

@router.callback_query(F.data == "vote_prince")
async def show_princes(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверяем, голосовал ли уже пользователь за принца
    if db.has_user_voted(user_id, vote_for_prince=True):
        await callback.answer("❌ Вы уже проголосовали за принца!", show_alert=True)
        return
    
    # Получаем список мужчин для голосования
    men_for_voting = db.get_users_for_voting(exclude_id=user_id, gender=True)  # True = мужчины
    
    if not men_for_voting:
        await callback.answer("❌ Пока нет участников-мужчин для голосования!", show_alert=True)
        return
    
    # Создаем клавиатуру для голосования за принцев
    keyboard = []
    for user_data in men_for_voting:
        keyboard.append([InlineKeyboardButton(
            text=f"👑 {user_data['fio']} (Голосов: {user_data['vote_count']})", 
            callback_data=f"show_prince_{user_data['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_voting_menu")])
    
    vote_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.delete()  # Удаляем предыдущее сообщение
    await callback.message.answer("Выберите принца для просмотра:", reply_markup=vote_keyboard)
    await callback.answer()

@router.callback_query(F.data == "vote_princess")
async def show_princesses(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверяем, голосовал ли уже пользователь за принцессу
    if db.has_user_voted(user_id, vote_for_prince=False):
        await callback.answer("❌ Вы уже проголосовали за принцессу!", show_alert=True)
        return
    
    # Получаем список девушек для голосования
    women_for_voting = db.get_users_for_voting(exclude_id=user_id, gender=False)  # False = женщины
    
    if not women_for_voting:
        await callback.answer("❌ Пока нет участниц-девушек для голосования!", show_alert=True)
        return
    
    # Создаем клавиатуру для голосования за принцесс
    keyboard = []
    for user_data in women_for_voting:
        keyboard.append([InlineKeyboardButton(
            text=f"👸 {user_data['fio']} (Голосов: {user_data['vote_count']})", 
            callback_data=f"show_princess_{user_data['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_voting_menu")])
    
    vote_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.delete()  # Удаляем предыдущее сообщение
    await callback.message.answer("Выберите принцессу для просмотра:", reply_markup=vote_keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("show_prince_"))
async def show_prince_details(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    # Получаем информацию о пользователе
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    # Проверяем, голосовал ли уже текущий пользователь за принца
    voter_id = callback.from_user.id
    has_voted_for_prince = db.has_user_voted(voter_id, vote_for_prince=True)
    
    # Отправляем информацию о принце с фото
    caption = f"👑 <b>Принц: {user['fio']}</b>\n\n"
    caption += f"📝 <b>О себе:</b>\n{user['description']}\n\n"
    caption += f"❤️ Голосов: {user['vote_count']}"
    
    # Создаем клавиатуру
    keyboard_buttons = []
    
    if not has_voted_for_prince:
        keyboard_buttons.append([InlineKeyboardButton(text="✅ Проголосовать за этого принца", callback_data=f"vote_prince_{user_id}")])
    
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад к списку принцев", callback_data="vote_prince")])
    keyboard_buttons.append([InlineKeyboardButton(text="🏠 В главное меню голосования", callback_data="back_to_voting_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Отправляем фото с информацией
    await callback.message.delete()  # Удаляем предыдущее сообщение
    await callback.message.answer_photo(
        photo=user['photo_id'],
        caption=caption,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("show_princess_"))
async def show_princess_details(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    # Получаем информацию о пользователе
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    # Проверяем, голосовал ли уже текущий пользователь за принцессу
    voter_id = callback.from_user.id
    has_voted_for_princess = db.has_user_voted(voter_id, vote_for_prince=False)
    
    # Отправляем информацию о принцессе с фото
    caption = f"👸 <b>Принцесса: {user['fio']}</b>\n\n"
    caption += f"📝 <b>О себе:</b>\n{user['description']}\n\n"
    caption += f"❤️ Голосов: {user['vote_count']}"
    
    # Создаем клавиатуру
    keyboard_buttons = []
    
    if not has_voted_for_princess:
        keyboard_buttons.append([InlineKeyboardButton(text="✅ Проголосовать за эту принцессу", callback_data=f"vote_princess_{user_id}")])
    
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад к списку принцесс", callback_data="vote_princess")])
    keyboard_buttons.append([InlineKeyboardButton(text="🏠 В главное меню голосования", callback_data="back_to_voting_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Отправляем фото с информацией
    await callback.message.delete()  # Удаляем предыдущее сообщение
    await callback.message.answer_photo(
        photo=user['photo_id'],
        caption=caption,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("vote_prince_"))
async def process_prince_vote(callback: types.CallbackQuery):
    voter_id = callback.from_user.id
    target_id = int(callback.data.split("_")[2])
    
    # Проверяем, голосовал ли уже пользователь за принца
    if db.has_user_voted(voter_id, vote_for_prince=True):
        await callback.answer("❌ Вы уже проголосовали за принца!", show_alert=True)
        return
    
    # Обрабатываем голосование за принца
    if db.process_vote(voter_id, target_id, vote_for_prince=True):
        target_user = db.get_user(target_id)
        
        # Обновляем сообщение с результатом
        caption = f"✅ Вы успешно проголосовали за принца <b>{target_user['fio']}</b>!\n\n"
        caption += f"👑 <b>Принц: {target_user['fio']}</b>\n\n"
        caption += f"📝 <b>О себе:</b>\n{target_user['description']}\n\n"
        caption += f"❤️ Голосов: {target_user['vote_count']}"
        
        # Создаем клавиатуру для перехода к голосованию за принцессу
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👸 Проголосовать за принцессу", callback_data="vote_princess")
            ],
            [InlineKeyboardButton(text="🏠 В главное меню голосования", callback_data="back_to_voting_menu")]
        ])
        
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.answer("❌ Не удалось проголосовать. Возможно, вы уже голосовали.", show_alert=True)

@router.callback_query(F.data.startswith("vote_princess_"))
async def process_princess_vote(callback: types.CallbackQuery):
    voter_id = callback.from_user.id
    target_id = int(callback.data.split("_")[2])
    
    # Проверяем, голосовал ли уже пользователь за принцессу
    if db.has_user_voted(voter_id, vote_for_prince=False):
        await callback.answer("❌ Вы уже проголосовали за принцессу!", show_alert=True)
        return
    
    # Обрабатываем голосование за принцессу
    if db.process_vote(voter_id, target_id, vote_for_prince=False):
        target_user = db.get_user(target_id)
        
        # Обновляем сообщение с результатом
        caption = f"✅ Вы успешно проголосовали за принцессу <b>{target_user['fio']}</b>!\n\n"
        caption += f"👸 <b>Принцесса: {target_user['fio']}</b>\n\n"
        caption += f"📝 <b>О себе:</b>\n{target_user['description']}\n\n"
        caption += f"❤️ Голосов: {target_user['vote_count']}"
        
        # Создаем клавиатуру для перехода к голосованию за принца
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👑 Проголосовать за принца", callback_data="vote_prince")
            ],
            [InlineKeyboardButton(text="🏠 В главное меню голосования", callback_data="back_to_voting_menu")]
        ])
        
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.answer("❌ Не удалось проголосовать. Возможно, вы уже голосовали.", show_alert=True)