# routerRegistration.py
from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from DataBase.mainDB import UserDB

# Инициализация базы данных
db = UserDB()

router = Router()

class RegistrationStates(StatesGroup):
    fio = State()
    description = State()
    gender = State()
    photo = State()

@router.message(F.text == "📝 Регистрация")
async def registration_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Проверяем, зарегистрирован ли уже пользователь
    existing_user = db.get_user(user_id)
    if existing_user and existing_user['fio']!=None:
        await message.answer(f"✅ Вы уже зарегистрированы как: {existing_user['fio']}")
        return
    
    await message.answer("Введите ваше ФИО:")
    await state.set_state(RegistrationStates.fio)

@router.message(RegistrationStates.fio)
async def process_fio(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await message.answer("Введите описание о себе:")
    await state.set_state(RegistrationStates.description)

@router.message(RegistrationStates.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    # Создаем клавиатуру для выбора пола
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male")],
        [InlineKeyboardButton(text="👩 Женский", callback_data="gender_female")]
    ])
    
    await message.answer("Выберите ваш пол:", reply_markup=keyboard)
    await state.set_state(RegistrationStates.gender)

@router.callback_query(RegistrationStates.gender, F.data.startswith("gender_"))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[1]
    gender_bool = gender == "male"  # True для мужского, False для женского
    
    await state.update_data(gender=gender_bool)
    await callback.message.edit_text("Отправьте вашу фотографию:")
    await state.set_state(RegistrationStates.photo)
    await callback.answer()

@router.message(RegistrationStates.photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.photo:
        user_data = await state.get_data()
        
        success = db.update_user(
            user_id=message.from_user.id,
            fio=user_data.get("fio"),
            photo_id=message.photo[-1].file_id,
            gender=user_data.get("gender", True),
            description=user_data.get("description", "")
        )
        
        if success:
            await message.answer("✅ Регистрация завершена!")
        else:
            await message.answer("❌ Ошибка при регистрации. Возможно, вы уже зарегистрированы.")
        
        await state.clear()
    else:
        await message.answer("Пожалуйста, отправьте фотографию!")