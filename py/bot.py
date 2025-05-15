from __future__ import annotations

import asyncio
import logging
import random
import string
import tempfile

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InputFile, FSInputFile
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
import aiohttp
from pathlib import Path
import json

import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import BOT_TOKEN
from constants import main_keyboard, cancel_keyboard, currency_keyboard, POPULAR_CURRENCIES, categories_keyboard, \
    comment_keyboard, report_keyboard, settings_keyboard

from db.database import engine, Base
from sqlalchemy import select, and_, or_
from db.models import Expense, User, Account
from db.database import get_session


class Form(StatesGroup):
    menu = State()
    amount = State()
    currency = State()
    category = State()
    comment = State()
    report_get_data = State()
    join = State()
    settings = State()
    join_account_h = State()
    create_account = State()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_user(tg_id: int, session):
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
    if not user:
        user = User(tg_id=tg_id)
        session.add(user)
        await session.commit()
    return user


async def get_user_expenses(user_id: int):
    async for session in get_session():
        result = await session.execute(
            select(Expense).where(Expense.user_id == user_id)
        )
        return result.scalars().all()


async def add_expense(user_id: int,
                      amount: float,
                      currency: str,
                      category: str,
                      comment: str = ""):
    async for session in get_session():
        user: User = await session.scalar(
            select(User).where(User.tg_id == user_id)
        )
        if user is None:
            return

        expense = Expense(
            user_id=user_id,
            account_id=user.account_id,
            amount=amount,
            currency=currency,
            category=category,
            comment=comment,
            created_at=datetime.utcnow()
        )
        session.add(expense)
        await session.commit()


async def get_fact(number: int) -> str:
    url = f"http://numbersapi.com/{number}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return "Не удалось получить забавный факт"
            fact = await resp.text()

    return fact


async def generate_expense_report(days: int,
                                  user_id: int,
                                  session: AsyncSession) -> BytesIO:
    since = datetime.utcnow() - timedelta(days=days)

    user: User = await session.scalar(
        select(User).where(User.tg_id == user_id)
    )
    if user is None:
        raise ValueError("Пользователь не найден")

    if user.account_id is not None:
        account_filter = Expense.account_id == user.account_id
    else:
        account_filter = and_(
            Expense.account_id.is_(None),
            Expense.user_id == user_id
        )

    q = (
        select(
            Expense.category,
            func.sum(Expense.amount).label("total")
        )
        .where(
            account_filter,
            Expense.created_at >= since
        )
        .group_by(Expense.category)
    )
    result = await session.execute(q)
    data = result.all()

    if not data:
        buf = BytesIO()
        plt.figure(figsize=(4, 4))
        plt.text(0.5, 0.5, "Нет трат за период", ha="center", va="center", fontsize=14)
        plt.axis("off")
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf

    categories, totals = zip(*data)
    total_sum = sum(totals)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(totals, labels=categories, autopct="%1.1f%%", startangle=90)
    ax.set_title(f"Траты за {days} дн.", fontsize=14)

    plt.figtext(0.5, 0.02, f"Всего потрачено: {total_sum:.2f}", ha="center", fontsize=12)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


async def command_start(message: Message, state: FSMContext):
    async for session in get_session():
        await get_or_create_user(message.from_user.id, session)
    await state.set_state(Form.menu)
    await message.answer(
        "Ваши личные траты в удобном месте!\n\n"
        "Можете воспользоваться такими командами:\n"
        "/add — добавить трату\n"
        "/report — посмотреть отчет\n"
        "/cancel — отменить ввод\n"
        "/settings — настройки счета\n"
        "/last - последние 3 траты", reply_markup=main_keyboard
    )


async def settings_menu(message: Message, state: FSMContext):
    await state.set_state(Form.settings)
    await message.answer(
        "Выберете пункт:\n\n"
        "Подключиться к существующему счету - если вы хотите, чтобы ваши траты учитывались вместе с чужыми\n\n"
        "Создать новый счет - при создании принадлежит только вам, но вы можете поделиться им с кем-то\n\n"
        "Покинуть счет - отключиться от привязанного счета\n\n"
        "Получить код и пароль счета - для другого человека", reply_markup=settings_keyboard
    )


async def navigation_settings(message: Message, state: FSMContext):
    text = message.text.strip()

    if text == "Подключиться к существующему счету":
        await state.set_state(Form.join_account_h)
        await message.answer("Введите код счёта и пароль через пробел:")

    elif text == "Создать новый счет":
        await create_account(message, state)

    elif text == "Покинуть текущий счет":
        await leave_account(message, state)

    elif text == "Назад в меню":
        await state.set_state(Form.menu)
        await command_start(message, state)
    elif text == "Получить код и пароль счета":
        await show_account_credentials(message, state)

    else:
        await message.answer("Неизвестная команда. Пожалуйста, выберите из меню.")


async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state not in (Form.amount, Form.currency, Form.category, Form.comment, Form.report_get_data):
        return
    logging.info("Отмена на шаге %r", current_state)
    await state.clear()
    await state.set_state(Form.menu)
    await command_start(message, state)


async def add_expense_start(message: Message, state: FSMContext):
    await state.set_state(Form.amount)
    await message.answer(
        f"Начало добавления траты...\n"
        "Напишите, сколько денег вы потратили на покупку:", reply_markup=cancel_keyboard
    )


async def add_expense_amount(message: Message, state: FSMContext):
    try:
        temp = message.text.replace(",", ".").replace(" ", "")
        amount = float(temp)
        await state.update_data(amount=amount)
        await state.update_data(currency="RUB")
        await state.set_state(Form.category)
        await message.answer("Теперь введите категорию траты:", reply_markup=categories_keyboard)
    except ValueError:
        await message.answer("Введите число.")


# async def add_expense_currency(message: Message, state: FSMContext):
#     currency = message.text.upper().replace(" ", "")
#     if currency in POPULAR_CURRENCIES:
#         await state.update_data(currency=currency)
#         await state.set_state(Form.category)
#         await message.answer("Теперь введите категорию траты:", reply_markup=categories_keyboard)
#     else:
#         await message.answer("Походу такой валюты нет у нас в базе данных...((\nПопробуйте еще раз")


async def add_expense_category(message: Message, state: FSMContext):
    category = message.text
    await state.update_data(category=category)
    await state.set_state(Form.comment)
    await message.answer("Можете добавить комментарий или пропустить этот шаг:", reply_markup=comment_keyboard)


async def process_comment(message: Message, state: FSMContext):
    comment = message.text
    if comment.lower() == "пропустить":
        comment = ""

    data = await state.get_data()
    amount = data["amount"]
    currency = data["currency"]
    category = data["category"]

    await add_expense(
        user_id=message.from_user.id,
        amount=amount,
        currency=currency,
        category=category,
        comment=comment
    )

    fact = await get_fact(int(float(amount)))
    await message.answer(f"The expense is saved!\n\nFact: {fact}")
    await state.clear()
    await state.set_state(Form.menu)
    await command_start(message, state)


async def report_process(message: Message, state: FSMContext):
    await state.set_state(Form.report_get_data)
    await message.answer(
        f"Выберете сколько дней учитывать в отчете:",
        reply_markup=report_keyboard
    )


async def report_process_get_data(message: Message, state: FSMContext):
    await message.answer(
        f"Ваш запрос принят. Подождите..."
    )
    days = message.text.strip().split()[0]
    if message.text == "За весь период":
        days = "10000"
    try:
        async for session in get_session():
            buf: BytesIO = await generate_expense_report(int(days), message.from_user.id, session)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            buf.seek(0)
            tmp.write(buf.read())
            tmp_path = tmp.name

        photo = FSInputFile(tmp_path)
        await message.answer_photo(photo, caption="Вот ваш отчёт")

        import os
        os.remove(tmp_path)
        await command_start(message, state)

    except ValueError:
        await message.answer(
            f"Не получилось понять сколько это дней... Попробуйте написать количество дней"
        )


async def leave_account(message: Message, state: FSMContext):
    async for session in get_session():
        user = await get_or_create_user(message.from_user.id, session)

        if not user.account_id:
            await message.answer("Вы не подключены ни к какому счёту.")
            return

        user.account_id = None
        await session.commit()

    await message.answer("Вы вышли из общего счёта. Ваши старые траты сохранены.")
    await state.set_state(Form.menu)
    await command_start(message, state)


async def create_account(message: Message, state: FSMContext):
    async for session in get_session():
        user = await get_or_create_user(message.from_user.id, session)

        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

        account = Account(code=code, password=password)
        session.add(account)
        await session.flush()

        user.account_id = account.id
        await session.commit()

    await message.answer(
        f"Новый счёт создан!\n\n"
        f"Код счёта: {code}\n"
        f"Пароль: {password}\n\n"
        "Передайте эти данные тем, с кем хотите поделиться."
    )

    await state.set_state(Form.menu)
    await command_start(message, state)


async def process_join(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("Неверный формат. Попробуйте ещё раз:\n<code>код пароль</code>")
        return

    code, password = parts
    async for session in get_session():
        account = await session.scalar(
            select(Account).where(Account.code == code, Account.password == password)
        )
        if not account:
            await message.answer("Неверный код или пароль. Попробуйте ещё.")
            return

        user = await get_or_create_user(message.from_user.id, session)
        user.account_id = account.id
        await session.commit()

    await message.answer("Вы успешно подключились к счёту!")
    await state.clear()
    await state.set_state(Form.menu)
    await command_start(message, state)


async def show_account_credentials(message: Message, state: FSMContext):
    async for session in get_session():
        user: User = await get_or_create_user(message.from_user.id, session)

        if not user.account_id:
            await message.answer("Вы не подключены ни к какому счёту.")
            await state.set_state(Form.menu)
            await command_start(message, state)
            return

        account: Account = await session.scalar(
            select(Account).where(Account.id == user.account_id)
        )
        if not account:
            await message.answer("Ошибка: ваш счёт не найден. Обратитесь к администратору.")
            await state.set_state(Form.menu)
            await command_start(message, state)
            return

        await message.answer(
            f"Если вы хотите поделиться счетом, то пусть человек перешлет следующее сообщение сюда же (Код и пароль):"
        )
        await message.answer(
            f"{account.code} {account.password}"
        )

    await state.set_state(Form.menu)
    await command_start(message, state)


async def show_last_expenses(message: Message, state: FSMContext):
    async for session in get_session():
        user = await session.scalar(select(User).where(User.tg_id == message.from_user.id))
        if not user:
            await message.answer("Вы ещё не зарегистрированы.")
            await command_start(message, state)
            return

        q = (
            select(Expense)
            .where(Expense.user_id == user.tg_id)
            .order_by(Expense.created_at.desc())
            .limit(3)
        )
        result = await session.execute(q)
        expenses = result.scalars().all()

        if not expenses:
            await message.answer("У вас пока нет трат.")
            await command_start(message, state)
            return

        text = "Последние траты:\n\n"
        for e in expenses:
            text += f"{e.amount} {e.currency} — {e.category}\n {e.created_at.strftime('%d.%m.%Y %H:%M')}\n {e.comment or '—'}\n\n"

        await message.answer(text.strip())
        await state.set_state(Form.menu)
        await command_start(message, state)


async def err_mess(message: Message, state: FSMContext):
    await state.set_state(Form.menu)
    await message.answer(
        f"Непонятки"
    )
    await command_start(message, state)


async def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(command_start, CommandStart())
    dp.message.register(cancel_handler, Command("cancel"))
    dp.message.register(cancel_handler, F.text.casefold() == "отменить")
    dp.message.register(add_expense_start, Command("add"))
    dp.message.register(add_expense_start, F.text.casefold() == "добавить трату")
    dp.message.register(report_process, Command("report"))
    dp.message.register(report_process, F.text.casefold() == "получить отчет")
    dp.message.register(report_process, Command("last"))
    dp.message.register(show_last_expenses, F.text.casefold() == "последние 3 траты")
    dp.message.register(report_process_get_data, Form.report_get_data)
    dp.message.register(add_expense_amount, Form.amount)
    dp.message.register(navigation_settings, Form.settings)
    dp.message.register(process_join, Form.join_account_h)
    dp.message.register(settings_menu, Command("settings"))
    dp.message.register(settings_menu, F.text.casefold() == "настройки")

    # dp.message.register(add_expense_currency, Form.currency)
    dp.message.register(add_expense_category, Form.category)
    dp.message.register(process_comment, Form.comment)
    dp.message.register(err_mess, Form.menu)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
