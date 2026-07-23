# Telegram-бот для фиксации заявок клиентов

MVP-версия партнёрского бота для сбора и сохранения заявок клиентов.

**Бот доступен в Telegram как @flowhack_bot**

## Функционал

- `/start` — приветствие и меню с кнопкой «Зафиксировать клиента»
- Пошаговый опрос: телефон клиента → телефон риелтора → ФИО клиента
- Валидация и приведение номеров к формату `+7XXXXXXXXXX`
- Сохранение заявки в SQLite (`database.db`)
- Защита от дублей: повторный телефон клиента → «Клиент уже в работе»

## Требования

- Python 3.10 или выше
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))

## Технологии

- Python 3.10+
- aiogram 3.x
- SQLite3
- python-dotenv

## Установка и запуск

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd rekruter-test-task

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Указать токен бота
#    Скопируйте .env и укажите токен, полученный от @BotFather:
#    TG_BOT_TOKEN=ваш_токен_здесь

# 5. Запустить
python bot.py

# Остановка: Ctrl+C
```

## Структура проекта

```
├── bot.py          # Основная логика бота, FSM, хендлеры
├── database.py     # Работа с БД SQLite (инициализация, сохранение, валидация)
├── .env            # Токен бота
├── .gitignore
├── requirements.txt
└── README.md
```
