"""Модуль для работы с БД SQLite."""

import logging
import os
import re
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)

DB_DIR: str = os.path.dirname(os.path.abspath(__file__))
DB_PATH: str = os.path.join(DB_DIR, "database.db")


def init_db() -> None:
    """Создаёт таблицу clients, если её нет."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_phone TEXT UNIQUE NOT NULL,
                    realtor_phone TEXT NOT NULL,
                    client_fio TEXT NOT NULL
                )
                """
            )
            conn.commit()
        logger.info("База данных инициализирована: %s", DB_PATH)
    except sqlite3.Error as exc:
        logger.error("Ошибка инициализации БД: %s", exc)
        raise


def save_client(
    client_phone: str, realtor_phone: str, client_fio: str
) -> None:
    """Сохраняет запись клиента в БД.

    Args:
        client_phone: Номер телефона клиента.
        realtor_phone: Номер телефона риелтора.
        client_fio: ФИО клиента.

    Raises:
        sqlite3.IntegrityError: Если client_phone уже существует.
        sqlite3.Error: При других ошибках БД.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO clients (client_phone, realtor_phone, client_fio)
                VALUES (?, ?, ?)
                """,
                (client_phone, realtor_phone, client_fio),
            )
            conn.commit()
        logger.info(
            "Сохранён клиент: %s, телефон: %s", client_fio, client_phone
        )
    except sqlite3.IntegrityError:
        logger.warning(
            "Дубликат: клиент %s уже существует", client_phone
        )
        raise
    except sqlite3.Error as exc:
        logger.error(
            "Ошибка БД при сохранении клиента %s: %s", client_phone, exc
        )
        raise


def validate_phone(raw: str) -> Optional[str]:
    """Очищает и валидирует номер телефона.

    Удаляет все нецифровые символы. Приводит номер к формату +7XXXXXXXXXX.

    Правила:
    - 11 цифр, первая 7 или 8 -> замена первой цифры на +7
    - 10 цифр, первая 7 или 8 -> добавление + в начало
    - 10 цифр, первая не 7/8  -> добавление +7 в начало
    - иначе -> None

    Примеры:
        '+7 (999) 123-45-67' -> '+79991234567'
        '8-999-123-45-67'    -> '+79991234567'
        '9991234567'         -> '+79991234567'
        '7999123456'         -> '+7999123456'

    Args:
        raw: Сырая строка с номером.

    Returns:
        Отформатированный номер или None при неверном формате.
    """
    digits: str = re.sub(r"\D", "", raw)

    if len(digits) == 11 and digits[0] in ("7", "8"):
        return f"+7{digits[1:]}"
    if len(digits) == 10:
        if digits[0] in ("7", "8"):
            return f"+{digits}"
        return f"+7{digits}"

    return None
