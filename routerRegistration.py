# routerRegistration.py
from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram import F
from aiogram.fsm.state import State, StatesGroup

from DataBase.mainDB import UserDB

# Инициализация базы данных
db = UserDB()

router = Router()

class RegistrationStates(StatesGroup):
    fio = State()
    description = State()
    photo = State()

@router.message(F.text == "📝 Регистрация")
async def registration_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Проверяем, зарегистрирован ли уже пользователь
    existing_user = db.get_user(user_id)
    if existing_user:
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
    await message.answer("Отправьте вашу фотографию:")
    await state.set_state(RegistrationStates.photo)

@router.message(RegistrationStates.photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.photo:
        user_data = await state.get_data()
        
        # Сохраняем пользователя в БД
        success = db.add_user(
            user_id=message.from_user.id,
            fio=user_data.get("fio"),
            photo_id=message.photo[-1].file_id,
            description=user_data.get("description", "")
        )
        
        if success:
            await message.answer("✅ Регистрация завершена!")
        else:
            await message.answer("❌ Ошибка при регистрации. Возможно, вы уже зарегистрированы.")
        
        await state.clear()
    else:
        await message.answer("Пожалуйста, отправьте фотографию!")