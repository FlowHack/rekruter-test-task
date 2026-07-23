"""Основной модуль Telegram-бота для фиксации заявок клиентов."""

import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.exceptions import TelegramNetworkError
from aiogram.utils.token import TokenValidationError
from dotenv import load_dotenv

from database import check_client_exists, init_db, save_client, validate_phone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

BUTTON_TEXT: str = "Зафиксировать клиента"
dp: Dispatcher = Dispatcher()


class ClientForm(StatesGroup):
    # pylint: disable=too-few-public-methods
    # StatesGroup из aiogram не требует публичных методов,
    # состояния определяются через атрибуты State()
    """Состояния для опроса данных клиента."""

    client_phone = State()
    realtor_phone = State()
    client_fio = State()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой 'Зафиксировать клиента'."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BUTTON_TEXT)]],
        resize_keyboard=True,
    )


def _get_user_id(message: Message) -> int:
    """Безопасно получает ID пользователя из сообщения."""
    user = message.from_user
    if user is None:
        return 0
    return user.id


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обрабатывает команду /start."""
    await message.answer(
        "Привет! Я бот для фиксации заявок клиентов.",
        reply_markup=get_main_keyboard(),
    )
    logger.info("Пользователь %s запустил бота", _get_user_id(message))


@dp.message(F.text & (F.text.lower() == BUTTON_TEXT.lower()))
async def start_registration(message: Message, state: FSMContext) -> None:
    """Запускает цепочку FSM для регистрации клиента."""
    await state.set_state(ClientForm.client_phone)
    await message.answer(
        "Введите номер телефона клиента:",
        reply_markup=ReplyKeyboardRemove(),
    )
    logger.info(
        "Пользователь %s начал регистрацию клиента",
        _get_user_id(message),
    )


@dp.message(ClientForm.client_phone)
async def process_client_phone(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод телефона клиента."""
    if not message.text:
        await message.answer("Пожалуйста, введите номер телефона текстом.")
        return
    phone: str | None = validate_phone(message.text)
    if phone is None:
        await message.answer(
            "Некорректный формат. Пожалуйста, введите номер телефона "
            "в формате +79991234567"
        )
        return

    if check_client_exists(phone):
        logger.warning("Дубликат: клиент %s уже существует", phone)
        await message.answer(
            "Клиент уже в работе",
            reply_markup=get_main_keyboard(),
        )
        await state.clear()
        return

    await state.update_data(client_phone=phone)
    await state.set_state(ClientForm.realtor_phone)
    await message.answer("Введите номер телефона риелтора:")
    logger.info("Телефон клиента принят: %s", phone)


@dp.message(ClientForm.realtor_phone)
async def process_realtor_phone(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод телефона риелтора."""
    if not message.text:
        await message.answer("Пожалуйста, введите номер телефона текстом.")
        return
    phone: str | None = validate_phone(message.text)
    if phone is None:
        await message.answer(
            "Некорректный формат. Пожалуйста, введите номер телефона "
            "в формате +79991234567"
        )
        return

    await state.update_data(realtor_phone=phone)
    await state.set_state(ClientForm.client_fio)
    await message.answer("Введите ФИО клиента:")
    logger.info("Телефон риелтора принят: %s", phone)


@dp.message(ClientForm.client_fio)
async def process_client_fio(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод ФИО и сохраняет данные в БД."""
    if not message.text:
        await message.answer("Пожалуйста, введите ФИО клиента текстом.")
        return
    fio: str = message.text.strip()
    if not fio:
        await message.answer("ФИО не может быть пустым. Введите ФИО клиента:")
        return

    data: dict[str, str | None] = await state.get_data()
    client_phone: str | None = data.get("client_phone")
    realtor_phone: str | None = data.get("realtor_phone")

    if not client_phone or not realtor_phone:
        logger.error(
            "Потеряны данные FSM для пользователя %s",
            _get_user_id(message),
        )
        await message.answer(
            "Произошла ошибка. Начните регистрацию заново.",
            reply_markup=get_main_keyboard(),
        )
        await state.clear()
        return

    try:
        save_client(client_phone, realtor_phone, fio)
        await message.answer(
            "Клиент зафиксирован",
            reply_markup=get_main_keyboard(),
        )
        logger.info(
            "Клиент %s (%s) успешно сохранён", fio, client_phone
        )
    except sqlite3.IntegrityError:
        logger.warning(
            "Попытка дубликата: клиент %s уже существует", client_phone
        )
        await message.answer(
            "Клиент уже в работе",
            reply_markup=get_main_keyboard(),
        )
    except sqlite3.Error as exc:
        logger.error(
            "Ошибка БД при сохранении клиента %s: %s", client_phone, exc
        )
        await message.answer(
            "Произошла ошибка при сохранении. Попробуйте позже.",
            reply_markup=get_main_keyboard(),
        )
    finally:
        await state.clear()


async def on_shutdown() -> None:
    """Действия при остановке бота."""
    logger.info("Бот останавливается...")


async def main() -> None:
    """Точка входа: инициализация БД и запуск polling."""
    init_db()

    token: str = os.getenv("TG_BOT_TOKEN", "")
    if not token:
        raise ValueError("TG_BOT_TOKEN не найден в .env")

    try:
        bot: Bot = Bot(token=token)
    except TokenValidationError as exc:
        logger.error("Неверный формат токена: %s", exc)
        raise

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except TelegramNetworkError as exc:
        logger.warning("Не удалось сбросить webhook: %s", exc)

    try:
        me = await bot.get_me()
        logger.info("Бот @%s запущен", me.username)
    except TelegramNetworkError as exc:
        logger.error(
            "Не удалось подключиться к Telegram. Проверьте токен и "
            "подключение к интернету: %s", exc
        )
        await bot.session.close()
        return

    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, skip_updates=True)
    except TelegramNetworkError as exc:
        logger.error("Бот остановлен из-за ошибки сети: %s", exc)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
