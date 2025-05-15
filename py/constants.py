from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='Добавить трату'), KeyboardButton(text='Получить отчет')],
              [KeyboardButton(text='Настройки'), KeyboardButton(text='Последние 3 траты')]], resize_keyboard=True,
    one_time_keyboard=True)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='Отменить')]], resize_keyboard=True,
    one_time_keyboard=True)

currency_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='USD'), KeyboardButton(text='RUB'), KeyboardButton(text='EUR'),
               KeyboardButton(text='Отменить')]],
    resize_keyboard=True,
    one_time_keyboard=True)

categories_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='Еда'), KeyboardButton(text='Транспорт'), KeyboardButton(text='Развлечения')],
              [KeyboardButton(text='Дом'), KeyboardButton(text='Покупки'), KeyboardButton(text='Отменить')]],
    resize_keyboard=True,
    one_time_keyboard=True)

comment_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='Пропустить'), KeyboardButton(text='Отменить')]],
    resize_keyboard=True,
    one_time_keyboard=True)

report_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='1 день'), KeyboardButton(text='7 дней'), KeyboardButton(text='30 дней')],
              [KeyboardButton(text='90 дней'), KeyboardButton(text='За весь период'), KeyboardButton(text='Отменить')]],
    resize_keyboard=True,
    one_time_keyboard=True)

settings_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='Подключиться к существующему счету'), KeyboardButton(text='Создать новый счет')],
              [KeyboardButton(text='Покинуть текущий счет'), KeyboardButton(text='Получить код и пароль счета'),
               KeyboardButton(text='Назад в меню')]],
    resize_keyboard=True,
    one_time_keyboard=True)

DEFAULT_CATEGORIES = ["Еда", "Транспорт", "Развлечения", "Дом", "Покупки"]

POPULAR_CURRENCIES = [
    "USD",  # Доллар США
    "EUR",  # Евро
    "RUB",  # Российский рубль
    "GBP",  # Британский фунт
    "JPY",  # Японская иена
    "CNY",  # Китайский юань
    "CHF",  # Швейцарский франк
    "CAD",  # Канадский доллар
    "AUD",  # Австралийский доллар
    "NZD",  # Новозеландский доллар
    "TRY",  # Турецкая лира
    "UAH",  # Украинская гривна
    "PLN",  # Польский злотый
    "KZT",  # Казахский тенге
    "INR",  # Индийская рупия
    "BRL",  # Бразильский реал
    "ZAR",  # Южноафриканский ранд
    "SEK",  # Шведская крона
    "NOK",  # Норвежская крона
    "DKK",  # Датская крона
    "HKD",  # Гонконгский доллар
    "SGD",  # Сингапурский доллар
    "MXN",  # Мексиканское песо
    "AED",  # Дирхам ОАЭ
    "CZK",  # Чешская крона
    "HUF",  # Венгерский форинт
]
