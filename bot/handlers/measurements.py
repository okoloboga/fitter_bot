"""
Обработчики раздела параметров пользователя
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states.measurements import MeasurementStates
from bot.keyboards.measurements import (
    get_start_measurements_keyboard,
    get_cancel_keyboard,
    get_measurements_actions_keyboard,
    get_edit_measurements_keyboard
)
from bot.keyboards.main_menu import get_main_menu
from bot.utils.api_client import api_client # Use API client for persistence

router = Router()


MEASUREMENTS_INFO_TEXT = """📐 Мои параметры

Укажи свои параметры, чтобы мы могли рекомендовать подходящий размер для каждого товара!

Нам понадобятся:
• Рост (в сантиметрах)
• Обхват груди (в сантиметрах)
• Обхват талии (в сантиметрах)
• Обхват бедер (в сантиметрах)

Это займет меньше минуты! ⏱"""


def format_measurements_text(measurements: dict) -> str:
    """Форматировать текст с параметрами"""
    return f"""✨ Твои параметры:

• Рост: {measurements.get('height', 'N/A')} см
• Обхват груди: {measurements.get('chest', 'N/A')} см
• Обхват талии: {measurements.get('waist', 'N/A')} см
• Обхват бедер: {measurements.get('hips', 'N/A')} см

Теперь мы будем показывать рекомендуемый размер для каждого товара!"""


@router.callback_query(F.data == "measurements")
async def show_measurements(callback: CallbackQuery):
    """Показать раздел параметров"""
    user_id = callback.from_user.id
    measurements = await api_client.get_measurements(user_id)

    if not measurements:
        await callback.message.edit_text(
            MEASUREMENTS_INFO_TEXT,
            reply_markup=get_start_measurements_keyboard()
        )
    else:
        await callback.message.edit_text(
            format_measurements_text(measurements),
            reply_markup=get_measurements_actions_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "measurements:view")
async def view_measurements_callback(callback: CallbackQuery):
    """Просмотр параметров через callback"""
    user_id = callback.from_user.id
    measurements = await api_client.get_measurements(user_id)

    if measurements:
        await callback.message.edit_text(
            format_measurements_text(measurements),
            reply_markup=get_measurements_actions_keyboard()
        )
    else:
        await callback.message.edit_text(
            MEASUREMENTS_INFO_TEXT,
            reply_markup=get_start_measurements_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "measurements:start")
async def start_measurements_input(callback: CallbackQuery, state: FSMContext):
    """Начать ввод параметров"""
    await state.set_state(MeasurementStates.waiting_height)
    await callback.message.edit_text(
        "Укажи свой рост в сантиметрах (например: 165)",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "measurements:cancel")
async def cancel_measurements_input(callback: CallbackQuery, state: FSMContext):
    """Отменить ввод параметров"""
    await state.clear()
    await callback.message.edit_text(
        "Ввод параметров отменен"
    )
    await callback.message.answer(
        "Выбери действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.message(MeasurementStates.waiting_height)
async def process_height(message: Message, state: FSMContext):
    """Обработка ввода роста"""
    try:
        height = int(message.text)
        if not (140 <= height <= 200):
            await message.answer(
                "Пожалуйста, введи корректное значение роста от 140 до 200 см",
                reply_markup=get_cancel_keyboard()
            )
            return
        await state.update_data(height=height)
        await state.set_state(MeasurementStates.waiting_chest)
        await message.answer(
            "Отлично! Теперь укажи обхват груди в сантиметрах (например: 85)",
            reply_markup=get_cancel_keyboard()
        )
    except ValueError:
        await message.answer(
            "Пожалуйста, введи число (например: 165)",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.waiting_chest)
async def process_chest(message: Message, state: FSMContext):
    """Обработка ввода обхвата груди"""
    try:
        chest = int(message.text)
        if not (70 <= chest <= 130):
            await message.answer(
                "Пожалуйста, введи корректное значение обхвата груди от 70 до 130 см",
                reply_markup=get_cancel_keyboard()
            )
            return
        await state.update_data(chest=chest)
        await state.set_state(MeasurementStates.waiting_waist)
        await message.answer(
            "Супер! Теперь обхват талии в сантиметрах (например: 65)",
            reply_markup=get_cancel_keyboard()
        )
    except ValueError:
        await message.answer(
            "Пожалуйста, введи число (например: 85)",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.waiting_waist)
async def process_waist(message: Message, state: FSMContext):
    """Обработка ввода обхвата талии"""
    try:
        waist = int(message.text)
        if not (50 <= waist <= 110):
            await message.answer(
                "Пожалуйста, введи корректное значение обхвата талии от 50 до 110 см",
                reply_markup=get_cancel_keyboard()
            )
            return
        await state.update_data(waist=waist)
        await state.set_state(MeasurementStates.waiting_hips)
        await message.answer(
            "Последний параметр! Укажи обхват бедер в сантиметрах (например: 95)",
            reply_markup=get_cancel_keyboard()
        )
    except ValueError:
        await message.answer(
            "Пожалуйста, введи число (например: 65)",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.waiting_hips)
async def process_hips(message: Message, state: FSMContext):
    """Обработка ввода обхвата бедер (финальный шаг)"""
    try:
        hips = int(message.text)
        if not (70 <= hips <= 140):
            await message.answer(
                "Пожалуйста, введи корректное значение обхвата бедер от 70 до 140 см",
                reply_markup=get_cancel_keyboard()
            )
            return

        data = await state.get_data()
        user_id = message.from_user.id
        
        # Save measurements via API
        await api_client.save_measurements(
            user_id,
            data['height'],
            data['chest'],
            data['waist'],
            hips
        )

        await state.clear()
        measurements = await api_client.get_measurements(user_id)
        await message.answer(
            format_measurements_text(measurements),
            reply_markup=get_measurements_actions_keyboard()
        )
    except ValueError:
        await message.answer(
            "Пожалуйста, введи число (например: 95)",
            reply_markup=get_cancel_keyboard()
        )


@router.callback_query(F.data == "measurements:edit_menu")
async def show_edit_menu(callback: CallbackQuery):
    """Показать меню редактирования параметров"""
    await callback.message.edit_text(
        "Какой параметр хочешь изменить?",
        reply_markup=get_edit_measurements_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("measurements:edit:"))
async def start_edit_parameter(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование конкретного параметра"""
    param = callback.data.split(":")[2]
    param_names = {
        "height": ("рост", "например: 165", MeasurementStates.editing_height),
        "chest": ("обхват груди", "например: 85", MeasurementStates.editing_chest),
        "waist": ("обхват талии", "например: 65", MeasurementStates.editing_waist),
        "hips": ("обхват бедер", "например: 95", MeasurementStates.editing_hips)
    }

    if param in param_names:
        param_name, example, state_to_set = param_names[param]
        await state.set_state(state_to_set)
        await callback.message.edit_text(
            f"Укажи {param_name} в сантиметрах ({example})",
            reply_markup=get_cancel_keyboard()
        )
    await callback.answer()


async def _update_single_measurement(message: Message, state: FSMContext, param_name: str, value: int):
    """Вспомогательная функция для обновления одного параметра"""
    user_id = message.from_user.id
    
    # Get current measurements
    current_measurements = await api_client.get_measurements(user_id)
    if not current_measurements:
        # This should not happen if user is editing, but as a safeguard
        current_measurements = {"height": 0, "chest": 0, "waist": 0, "hips": 0}
    
    # Update the specific parameter
    current_measurements[param_name] = value
    
    # Save all measurements via API
    await api_client.save_measurements(
        user_id,
        current_measurements['height'],
        current_measurements['chest'],
        current_measurements['waist'],
        current_measurements['hips']
    )
    
    await state.clear()
    updated_measurements = await api_client.get_measurements(user_id)
    await message.answer(
        format_measurements_text(updated_measurements),
        reply_markup=get_measurements_actions_keyboard()
    )


@router.message(MeasurementStates.editing_height)
async def edit_height(message: Message, state: FSMContext):
    """Редактирование роста"""
    try:
        height = int(message.text)
        if not (140 <= height <= 200):
            await message.answer(
                "Пожалуйста, введи корректное значение роста от 140 до 200 см",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "height", height)
    except ValueError:
        await message.answer(
            "Пожалуйста, введи число (например: 165)",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_chest)
async def edit_chest(message: Message, state: FSMContext):
    """Редактирование обхвата груди"""
    try:
        chest = int(message.text)
        if not (70 <= chest <= 130):
            await message.answer(
                "Пожалуйста, введи корректное значение обхвата груди от 70 до 130 см",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "chest", chest)
    except ValueError:
        await message.answer(
            "Пожалуйста, введи число (например: 85)",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_waist)
async def edit_waist(message: Message, state: FSMContext):
    """Редактирование обхвата талии"""
    try:
        waist = int(message.text)
        if not (50 <= waist <= 110):
            await message.answer(
                "Пожалуйста, введи корректное значение обхвата талии от 50 до 110 см",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "waist", waist)
    except ValueError:
        await message.answer(
            "Пожалуйста, введи число (например: 65)",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_hips)
async def edit_hips(message: Message, state: FSMContext):
    """Редактирование обхвата бедер"""
    try:
        hips = int(message.text)
        if not (70 <= hips <= 140):
            await message.answer(
                "Пожалуйста, введи корректное значение обхвата бедер от 70 до 140 см",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "hips", hips)
    except ValueError:
        await message.answer(
            "Пожалуйста, введи число (например: 95)",
            reply_markup=get_cancel_keyboard()
        )
