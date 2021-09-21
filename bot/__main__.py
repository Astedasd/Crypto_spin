import logging
from asyncio import sleep
from datetime import datetime, timedelta
from os import getenv
from sys import exit
import re

from aiogram import Bot, Dispatcher, types, md
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import BotBlocked
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.utils.markdown import bold, hbold

# работа с БД
from bot.db_service import get_user, register_user, update_username, get_referrals, update_balance
from bot.db_service import set_referral, get_blocked_users, block_user, save_action, get_all_users
# Работа с уведомлениями
from bot.db_service import create_notification, get_notifications, update_notifications_read, delete_notification
# Работа с рассылками
from bot.db_service import create_mailing, update_mailing, delete_mailing, get_mailings_to_send, get_mailing, get_last_mailing_id
# Работа с промокодами
from bot.db_service import create_promocode, get_promocode, get_all_promocodes, delete_promocode, get_last_promocode_id
from bot.db_service import promocode_activated, activate_promocode
# Работа с реф ссылками рекламных каналов
from bot.db_service import create_ref_link, delete_ref_link, get_ref_links
# Работа с платежными системами
from bot.db_service import get_waiting_deposits, update_deposit_status
# Работа со статистикой
from bot.db_service import prepare_daily_stat, get_platform_statistics

# Клавиатуры
from bot.keyboards import start_keyboard, cancel_keyboard, standard_keyboard, balance_keyboard
from bot.keyboards import support_keyboard, games_keyboard, joe_keyboard, joe_message, stake_keyboard
from bot.keyboards import admin_keyboard, promocodes_keyboard, ref_links_keyboard, statistics_keyboard
from bot.keyboards import deposit_method_keyboard, withdraw_method_keyboard, mailing_keyboard, mailing_inline_keyboard
from bot.keyboards import mailing_media_keyboard

# Шаблоны сообщений
from bot.keyboards import user_stat_message, platform_stat_message

# Уведомления
from bot.notifications import start_notification, deposit_success_notification

# Список администраторов
from bot.config import bot_name, admins, SPIN_TEXT, dollar, ROFL_VIDEO_ID

from bot.joe_game import get_casino_values, is_winning_combo

from bot.qiwi import create_qiwi_payment_link, check_qiwi_payment_status
from bot.coinbase import create_coinbase_payment_link, check_coinbase_payment_status

from bot.google_api import upload_statistics



# Токен берётся из переменной окружения (можно задать через systemd unit)
token = getenv("BOT_TOKEN")
if not token:
    exit("Error: no token provided")


# log level
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger.error("Starting Bot")
scheduler = AsyncIOScheduler()


# bot init
bot = Bot(token=token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
blocked_users = get_blocked_users()

# Временные переменные
stakes = []
"""
# Инициализация объектов бота, хранилища в памяти, логера и кэша (для троттлинга)
bot = Bot(token=token, parse_mode="HTML")
dp = Dispatcher(
    bot,
    storage=RedisStorage2(
        host=getenv("REDIS_HOST", "redis")
    )
)
logging.basicConfig(level=logging.INFO)"""


def schedule_jobs():
    scheduler.add_job(checking_deposits, "interval", seconds=300)
    scheduler.add_job(prepare_daily_statistics, "cron", hour='0', minute='0', timezone='utc')
    scheduler.add_job(prepare_ads_stats, "interval", seconds=3600)
    scheduler.add_job(send_mailings, "interval", seconds=60)


async def on_startup_notify(dp):
    await dp.bot.send_message(330639572, "Бот запущен")


async def on_startup(dp):
    await on_startup_notify(dp)
    await set_commands(dp)
    schedule_jobs()


async def checking_deposits():
    """
    Проверяем платежи со статусом NEW и WAITING
    deposit = {
        'deposit_id': payment[0],
        'user_id': payment[1],
        'amount': payment[2],
        'link': payment[3],
        'status': payment[4],
        'deposit_type': payment[5],
        'date': payment[6],
        }
    :return: None
    """
    deposits = get_waiting_deposits()
    if deposits:
        for deposit in deposits:
            datetime_format = "%Y-%m-%d %H:%M:%S.%f"
            payment_datetime = datetime.strptime(deposit['date'], datetime_format)
            if datetime.utcnow()-payment_datetime > timedelta(seconds=6000):
                # Удалить платеж
                update_deposit_status(deposit=deposit, new_status="EXPIRED")
                print(f"Просрочен платеж {deposit['deposit_id']} на сумму {deposit['amount']}")
            else:
                if deposit['deposit_type'] == "QIWI":
                    deposit_status = check_qiwi_payment_status(deposit)
                elif deposit['deposit_type'] == "COINBASE":
                    deposit_status = check_coinbase_payment_status(deposit)
                    pass
                if deposit_status == 'PAID':
                    # Обработка успешного платежа
                    update_deposit_status(deposit=deposit, new_status='PAID')
                    update_balance(user_id=deposit['user_id'], delta_money=float(deposit['amount']), delta_insurance=float(deposit['amount'])*0.1)
                    await send_balance_update(deposit['user_id'], deposit['amount'])
                    create_notification(user_id=deposit['user_id'],
                                        notification_text=deposit_success_notification(amount=deposit['amount']))
                    save_action(user_id=deposit['user_id'],
                                action=f"DEPOSIT: Пользователь {deposit['user_id']} пополнил баланс на {deposit['amount']}",
                                action_type="DEPOSIT")
                    print(f"Оплачен счет {deposit['deposit_id']} на сумму {deposit['amount']}")
                elif deposit_status in ('REJECTED',  'EXPIRED', 'CANCELED'):
                    update_deposit_status(deposit=deposit, new_status=deposit_status)
                    print(f"Отменен платеж {deposit['deposit_id']} на сумму {deposit['amount']}")
                else:
                    print(f"Ожидается платеж {deposit['deposit_id']} через {deposit['deposit_type']} "
                          f"на сумму {deposit['amount']}")
    else:
        print("no payments pending")


async def prepare_daily_statistics():
    # Заполнить таблицу статистики
    stats = prepare_daily_stat()
    # Закинуть все в гугл таблицу
    print("Готовлю ежедневную статистику")
    upload_statistics(stats=stats)
    pass


async def prepare_ads_stats():
    pass


async def send_balance_update(user_id: int, amount: float):
    """
    Отправляет сообщение пользователю, что его баланс успешно пополнен
    :param user_id: int
    :param amount: float
    :return:
    """
    await dp.bot.send_message(int(user_id), f"Ваш баланс пополнен на {amount}$")


async def set_commands(dispatcher):
    """
    Задает основные команды
    :param dispatcher:
    :return:
    """
    commands = [
        types.BotCommand(command="start", description="Перезапустить казино"),
        # types.BotCommand(command="reset", description="Перезапустить бота"),
        # types.BotCommand(command="help", description="Справочная информация")
    ]
    await bot.set_my_commands(commands)


async def send_mailings():
    mailings = get_mailings_to_send()
    if mailings:
        for mailing in mailings:
            try:
                time_format = '%Y-%m-%d %H:%M'
                mailing_date = datetime.strptime(mailing['mailing_date'], time_format)
                if mailing_date < datetime.utcnow():
                    users = get_all_users()
                    # users = (get_user(330639572),)
                    for user in users:
                        if mailing['mailing_file_type'] == 'video':
                            await dp.bot.send_video(chat_id=user['user_id'], video=mailing['mailing_file_id'])
                        elif mailing['mailing_file_type'] == 'photo':
                            await dp.bot.send_photo(chat_id=user['user_id'], photo=mailing['mailing_file_id'])
                        elif mailing['mailing_file_type'] == 'animation':
                            await dp.bot.send_animation(chat_id=user['user_id'], animation=mailing['mailing_file_id'])
                        await dp.bot.send_message(chat_id=user['user_id'], text=mailing['mailing_text'])
                    mailing['mailing_status'] = 'SENT'
                    update_mailing(mailing)
            except Exception as e:
                pass
    else:
        print("No mailings to send")
        return


# States
class States(StatesGroup):
    entering_promocode = State()  # Пользователь вводит промокод
    playing_joe = State()  # Пользователь находится в игре
    administrating = State()  # Администратор в админ панели
    admin_blocking = State()  # Администратор вводит id пользователя для блока
    creating_promocode_name = State()  # Администратор вводит название нового промокода
    creating_promocode_sum = State()  # Администратор вводит сумму нового промокода
    creating_ref_link = State()
    entering_deposit = State()  # пользователь вводит сумму для пополнения баланса
    entering_withdraw = State()  # пользователь вводит сумму для вывода баланса
    entering_username = State()
    entering_date = State()  # Админ вводит дату, чтобы посмотреть статистику платформы в этот день
    entering_mailing_text = State()  # Админ вводит текст рассылки
    sending_mailing_file = State()  # Админ присылает файл для рассылки
    entering_mailing_date = State()  # Админ вводит дату рассылки


@dp.message_handler(user_id=blocked_users)
async def handle_banned(message: types.Message):
    # print(f"{message.from_user.full_name} пишет, но мы ему не ответим!")
    return True


# Обработка команды start
@dp.message_handler(commands='start')
async def cmd_start(message: types.Message, state: FSMContext):
    # Регистрируем пользователя
    keyboard_1, keyboard_2 = start_keyboard()
    text1 = "Приветствую! Перед началом игры прошу Вас ознакомиться с условиями  и правилами"
    text2 = "Подтвердите, пожалуйста, соглашение"

    # обработка реферальной ссылки
    referrer = None
    if " " in message.text:
        referrer_id = message.text.split()[1]
        # Пробуем преобразовать строку в число
        try:
            referrer_id = int(referrer_id)
            if message.from_user['id'] != referrer_id and get_user(referrer_id):
                referrer = referrer_id
        except ValueError:
            pass
    # Проверка регистрации
    if register_user(message.from_user['id'], message.from_user['username']):
        if referrer:
            set_referral(referrer, message.from_user['id'])
        await message.answer(text1, reply_markup=keyboard_1)
        await message.answer(text2, reply_markup=keyboard_2)

    else:
        if get_user(message.from_user['id']):
            await message.answer_video(ROFL_VIDEO_ID)
            await message.answer(f"Главное меню",
                                 reply_markup=standard_keyboard(message.from_user['id']))
        else:
            await message.answer(text1, reply_markup=keyboard_1)
            await message.answer(text2, reply_markup=keyboard_2)


# Проверка наличия у пользователя username
@dp.callback_query_handler(Text(equals="ready_to_start"))
async def ready_to_start(call: types.CallbackQuery):
    if call.from_user['username']:
        update_username(user_id=call.from_user['id'], user_name=call.from_user['username'])
        create_notification(user_id=call.from_user['id'],
                            notification_text=start_notification(user_name={call.from_user['username']}))
        save_action(user_id=call.from_user['id'],
                    action=f"REGISTRATION: Пользователь {call.from_user['username']} успешно зарегистрировался",
                    action_type="REGISTRATION")
        await call.message.answer('Регистрация пройдена успешно', reply_markup=standard_keyboard(call.from_user['id']))
        await call.message.answer_video(video=ROFL_VIDEO_ID)
    else:
        await call.message.answer('Сначала поставь себе @username на аккаунт 😉',
                                  reply_markup=types.ReplyKeyboardRemove())
    await call.answer()


@dp.message_handler(content_types=[types.ContentType.VIDEO])
async def download_doc(message: types.Message):
    document = message.video
    print(document)
    await message.answer("Файл получен")


# Обработка команды отмена в админ панели
@dp.message_handler(state=States.admin_blocking, commands='отмена')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state=States.admin_blocking)
@dp.message_handler(Text(equals='отмена', ignore_case=True), state=States.administrating)
@dp.message_handler(Text(equals='отмена', ignore_case=True), state=States.creating_promocode_name)
@dp.message_handler(Text(equals='отмена', ignore_case=True), state=States.creating_promocode_sum)
@dp.message_handler(Text(equals='отмена', ignore_case=True), state=States.creating_ref_link)
async def cancel_handler(message: types.Message, state: FSMContext):
    await States.administrating.set()
    await message.answer('Отменено', reply_markup=admin_keyboard())


# Обработка команды отмена, сбрасывает state
@dp.message_handler(state='*', commands='отмена')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        # logging.info('Cancelling state %r', current_state)
        # Cancel state and inform user about it
        await state.finish()
    await message.answer('Отменено', reply_markup=standard_keyboard(message.from_user['id']))


########################################################################################################################
# ОСВНОВНОЕ МЕНЮ:
########################################################################################################################
# Обработка команды Игры
@dp.message_handler(text='Игры')
async def cmd_games(message: types.Message, state: FSMContext):
    await message.answer("Выберете игру:", reply_markup=games_keyboard())


########################################################################################################################
# ОДНОРУКИЙ ДЖО:
########################################################################################################################
# Играем в Однорукого Джо
@dp.callback_query_handler(Text(equals="play_joe"))
async def play_joe(call: types.CallbackQuery, state: FSMContext):
    await States.playing_joe.set()
    user = get_user(user=call.from_user['id'])
    balance = round(float(user['balance']), 2)
    insurance = round(float(user['insurance']), 2)
    result = 0.
    await state.update_data(balance=balance, stake=1.)
    await state.update_data(insurance=insurance, stake=0.)
    await state.update_data(result=0.)
    await state.update_data(stake=1.0)
    await call.message.answer(text=joe_message(balance, result, insurance),
                              parse_mode='HTML', reply_markup=joe_keyboard('1.0'))
    await call.answer()


@dp.message_handler(Text(equals="⬅"), state=States.playing_joe)
async def stake_down(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_stake = round(float(user_data.get("stake", 1.0)), 2)
    user_balance = round(float(user_data.get("balance")), 2)
    if user_stake > 1.0:
        if user_stake > user_balance:
            user_stake = user_balance
            await message.answer(f"Понижаю ставку до допустимого значения\nСтавка  =  ${user_stake}",
                                 reply_markup=joe_keyboard(user_stake))
        else:
            user_stake = user_stake - 1.0
            await message.answer(f"Понижаю ставку на $1\nСтавка  =  ${user_stake}",
                                 reply_markup=joe_keyboard(user_stake))
        await state.update_data(stake=user_stake)
        await message.answer(f"Понижаю ставку на $1\nСтавка  =  ${user_stake}", reply_markup=joe_keyboard(user_stake))
    else:
        await message.answer("Ставку меньше $1 можно установить из заданных, нажмите «Ставка»", reply_markup=joe_keyboard(user_stake))
    await message.delete()


@dp.message_handler(Text(equals="➡"), state=States.playing_joe)
async def stake_up(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_stake = round(float(user_data.get("stake", 1.)), 2)
    user_balance = round(float(user_data.get("balance")), 2)
    if user_stake < user_balance:
        user_stake = user_stake + 1.0
        await state.update_data(stake=user_stake)
        await message.answer(f"Повышаю ставку на $1\nСтавка  =  ${user_stake}", reply_markup=joe_keyboard(user_stake))
    else:
        user_stake = user_balance
        await message.answer("Ставка не может превышать баланс", reply_markup=joe_keyboard(user_stake))
    await message.delete()


@dp.message_handler(Text(equals="Max ставка"), state=States.playing_joe)
async def stake_max(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_stake = round(float(user_data.get("balance")), 2)
    await state.update_data(stake=user_stake)
    await message.answer(f"Повышаю ставку до максимальной\nСтавка  =  ${user_stake}",
                         reply_markup=joe_keyboard(user_stake))


@dp.message_handler(Text(startswith="Ставка"), state=States.playing_joe)
async def stake_choose(message: types.Message, state: FSMContext):
    await message.answer(f"Выбери свою ставку", reply_markup=stake_keyboard())


@dp.callback_query_handler(Text(equals="Назад"), state=States.playing_joe)
async def stake_back(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer()


@dp.callback_query_handler(Text(startswith="stake"), state=States.playing_joe)
async def stake_back(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    user_data = await state.get_data()
    user_balance = round(float(user_data.get("balance")), 2)
    user_stake = round(float(user_data.get("stake", 1.0)), 2)
    stake = round(float(call.data.split('_')[1]), 2)
    if stake < user_balance:
        user_stake = stake
        await state.update_data(stake=user_stake)
        await call.message.answer(f"Ставка  =  ${user_stake}",
                                  reply_markup=joe_keyboard(user_stake))
    else:
        await call.message.answer("Ставка не может превышать баланс", reply_markup=joe_keyboard(user_stake))
    await call.answer()


@dp.message_handler(Text(equals=SPIN_TEXT), state=States.playing_joe)
async def make_spin(message: types.Message, state: FSMContext):
    # Получение текущего счёта пользователя (или значения по умолчанию)
    user_data = await state.get_data()
    user_stake = round(float(user_data.get("stake", 1.0)), 2)
    user_balance = round(float(user_data.get("balance")), 2)
    user_insurance = round(float(user_data.get("insurance")), 2)
    #print("Начинаю крутить\nbalance =", user_balance, "\ninsurance =", user_insurance, "\nstake =", user_stake)
    if user_stake > user_balance:
        await message.answer("Ваша ставка превышает баланс")
        return
    if user_balance == 0.0:
        await message.answer("Ваш баланс равен нулю")
        return

    # Отправляем дайс и смотрим, что выпало
    msg = await message.answer_dice(emoji="🎰", reply_markup=joe_keyboard(user_stake))
    dice_combo = get_casino_values(msg.dice.value)
    if not dice_combo:
        await message.answer(f"Что-то пошло не так. Пожалуйста, попробуйте ещё раз. Проблема с dice №{msg.dice.value}")
        return

    # Проверяем, выигрышная комбинация или нет, обновляем счёт
    is_win, rate = is_winning_combo(dice_combo)
    delta = round(float(user_stake) * rate, 2)
    update_balance(user_id=message.from_user['id'], delta_money=delta, delta_insurance=0.0)
    user_balance = round(user_balance + delta, 2)
    await state.update_data(balance=user_balance)
    await state.update_data(result=delta)
    # Готовим сообщение о выигрыше/проигрыше и
    if is_win:
        save_action(user_id=message.from_user['id'],
                    action=f"WIN: Пользователь {message.from_user['username']} выиграл ${delta}",
                    action_type="WIN")
    else:
        save_action(user_id=message.from_user['id'],
                    action=f"LOSE: Пользователь {message.from_user['username']} проиграл ${delta}",
                    action_type="LOSE")

    # Имитируем задержку и отправляем ответ пользователю
    await sleep(2)
    if user_balance == 0.0:
        if user_insurance > 0.0:
            user_balance = user_insurance
            user_insurance = 0.0
            await state.update_data(insurance=user_insurance)
            await state.update_data(balance=user_balance)
            update_balance(user_id=message.from_user['id'], delta_money=user_balance, delta_insurance=-user_balance)
            save_action(user_id=message.from_user['id'],
                        action=f"INSURANCE: Пользователь {message.from_user['username']} "
                               f"воспользовался страховкой на сумму {user_balance}",
                        action_type="INSURANCE")
            create_notification(user_id=message.from_user['id'],
                                notification_text=f"Ваш счет пополнен на сумму {user_balance} за счет страховки")
            await message.answer(f"Ваш счет пополнен на сумму {user_balance} за счет страховки")
    await msg.reply(joe_message(user_balance, delta, user_insurance),
                    parse_mode='HTML', reply_markup=joe_keyboard(user_stake))
########################################################################################################################


# Выходим в главное меню
@dp.message_handler(state='*', commands='Выход')
@dp.message_handler(text="Выход", state='*')
async def exit_to_main_menu(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        logging.info('Cancelling state %r', current_state)
        # Cancel state and inform user about it
        await state.finish()
    await message.answer_video(ROFL_VIDEO_ID)
    await message.answer("Вы в главном меню", reply_markup=standard_keyboard(message.from_user['id']))


########################################################################################################################
# Обработка команды Баланс
@dp.message_handler(text='Баланс')
async def cmd_balance(message: types.Message, state: FSMContext):
    user = get_user(message.from_user['id'])
    await message.answer(f"Ваш баланс составляет: {user['balance']}", reply_markup=balance_keyboard())


# Обработка команды Пополнить
@dp.callback_query_handler(Text(equals="deposit"))
async def cmd_deposit(call: types.CallbackQuery):
    await States.entering_deposit.set()
    await call.message.answer("Введите сумму пополнения ($)", reply_markup=cancel_keyboard())
    await call.answer()


# Обработка считывания суммы пополнения
@dp.message_handler(state=States.entering_deposit)
async def cmd_deposit_create(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount > 0:
            await state.finish()
            await message.answer(f"Выберете метод оплаты:", reply_markup=deposit_method_keyboard(message.from_user['id'], message.text))
        else:
            await message.answer("Сумма пополнения введена неверно, введите число еще раз",
                                 reply_markup=cancel_keyboard())
    except Exception as e:
        await message.answer("Сумма пополнения введена неверно, введите число еще раз", reply_markup=cancel_keyboard())


# Выдаем ссылку на оплату
@dp.callback_query_handler(Text(startswith="deposit_"))
async def cmd_payment_link(call: types.CallbackQuery):
    await call.message.delete()
    user_id = call.data.split('_')[1]
    payment_type = call.data.split('_')[2]
    amount = call.data.split('_')[3]
    if payment_type == 'qiwi':
        link = create_qiwi_payment_link(user_id=user_id, amount=amount)
    elif payment_type == 'crypto':
        link = create_coinbase_payment_link(user_id=user_id, amount=amount)
    else:
        print("Какая-то ошибка с созданием платежа")
        return
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Оплатить счет", url=link))
    await call.message.answer(f"Создан счет на сумму ${amount}",
                              reply_markup=standard_keyboard(user_id))
    await call.message.answer(f"Оплатить можно по ссылке:", reply_markup=keyboard)
    await call.answer()


# Обработка команды Вывести
@dp.callback_query_handler(Text(equals="withdraw"))
async def cmd_withdraw(call: types.CallbackQuery):
    await States.entering_withdraw.set()
    await call.message.answer("Введите сумму для вывода ($)", reply_markup=cancel_keyboard())
    await call.answer()


# Обработка считывания суммы вывода
@dp.message_handler(state=States.entering_withdraw)
async def cmd_deposit_create(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount > 0:
            await state.finish()
            await message.answer(f"Выберете метод оплаты:", reply_markup=withdraw_method_keyboard(message.from_user['id'], message.text))
        else:
            await message.answer("Сумма вывода введена неверно, введите число еще раз",
                                 reply_markup=cancel_keyboard())
    except Exception as e:
        await message.answer("Сумма вывода введена неверно, введите число еще раз", reply_markup=cancel_keyboard())


# Фиксируем запрос вывода
@dp.callback_query_handler(Text(startswith="deposit_"))
async def cmd_payment_link(call: types.CallbackQuery):
    await call.message.delete()
    user_id = call.data.split('_')[1]
    payment_type = call.data.split('_')[2]
    amount = call.data.split('_')[3]
    """
    if payment_type == 'qiwi':
        link = create_qiwi_payment_link(user_id=user_id, amount=amount)
    elif payment_type == 'crypto':
        link = create_coinbase_payment_link(user_id=user_id, amount=amount)
    else:
        print("Какая-то ошибка с созданием платежа")
        return
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Оплатить счет", url=link))
    await call.message.answer(f"Создан счет на сумму ${amount}",
                              reply_markup=standard_keyboard(user_id))
    await call.message.answer(f"Оплатить можно по ссылке:", reply_markup=keyboard)
    """
    await call.message.answer(f"Ваш запрос на вывод сформирован. Запрос обрабатывается модератором в течение 24 часов.",
                              reply_markup=standard_keyboard(user_id))
    await call.answer()


# Получаем список рефералов пользователя
@dp.callback_query_handler(Text(equals="referrals"))
async def referrals(call: types.CallbackQuery):
    user_id = call.from_user['id']
    await call.message.answer(f"Ваша реферальная ссылка:\nhttp://t.me/{bot_name}?start={call.from_user['id']}",
                              reply_markup=standard_keyboard(call.from_user['id']))
    referrals = get_referrals(user_id)
    if referrals:
        text = "Ваши рефералы:"
        for referral in referrals:
            text = text + '\n' + str(referral)
        await call.message.answer(text)
    else:
        await call.message.answer("У вас нет рефералов")
    await call.answer()
########################################################################################################################


########################################################################################################################
# Хочет ввести промокод
@dp.callback_query_handler(Text(equals="activate_promocode"))
async def activate_promocodes(call: types.CallbackQuery):
    await call.message.delete()
    await States.entering_promocode.set()
    await call.message.answer("Введите промокод", reply_markup=cancel_keyboard())
    await call.answer()


# Считываем промокод
@dp.message_handler(state=States.entering_promocode)
async def checking_promocode(message: types.Message, state: FSMContext):
    promocode = get_promocode(message.text)
    if promocode:
        if not promocode_activated(user_id=message.from_user['id'], promocode_name=promocode['promocode_name']):
            # Добавить денег
            await state.finish()
            update_balance(user_id=message.from_user['id'], delta_money=promocode['promocode_sum'], delta_insurance=0.0)
            activate_promocode(user_id=message.from_user['id'], promocode_name=promocode['promocode_name'])
            save_action(user_id=message.from_user['id'],
                        action=f"PROMOCODE: Пользователь {message.from_user['username']} активировал промокод "
                               f"{message.text} на {promocode['promocode_sum']}$", action_type="PROMOCODE")
            create_notification(user_id=message.from_user['id'],
                                notification_text=f"Вы успешно активировали промокод {message.text} на {promocode['promocode_sum']}$")
            await message.answer(f"Отлично, вы получили {promocode['promocode_sum']}$",
                                 reply_markup=standard_keyboard(message.from_user['id']))
        else:
            await message.answer(f"Вы уже активировали данный промокод {promocode['promocode_name']}",
                                 reply_markup=cancel_keyboard())
    else:
        await message.answer("Такой промокод не существует.\nВведите действительный промокод",
                             reply_markup=cancel_keyboard())
########################################################################################################################

########################################################################################################################
# Обработка команды Уведомления
@dp.message_handler(Text(startswith='Уведомления'))
async def cmd_notifications(message: types.Message, state: FSMContext):
    notifications = get_notifications(message.from_user['id'])
    if notifications:
        await message.answer("Имеющиеся уведомления:", reply_markup=standard_keyboard(message.from_user['id']))
        for notification in notifications:
            keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=1)
            keyboard.add(types.InlineKeyboardButton(text='Удалить', callback_data=f"delete-notification_{notification['notification_id']}"))
            text = str(notification['notification_date']) + " " + str(notification['notification_text'])
            await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("Уведомлений нет", reply_markup=standard_keyboard(message.from_user['id']))


# Обработка удаления Уведомления
@dp.callback_query_handler(Text(startswith="delete-notification_"))
async def delete_notifications(call: types.CallbackQuery):
    notification_id = call.data.split('_')[1]
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.InlineKeyboardButton(text='Да', callback_data=f"yes_delete_{notification_id}"),
                 types.InlineKeyboardButton(text='Нет', callback_data=f"no_delete_{notification_id}"))
    await call.message.edit_reply_markup(keyboard)
    await call.answer()


# Обработка отмены удаления Уведомления
@dp.callback_query_handler(Text(startswith="no_delete"))
async def no_delete_notification(call: types.CallbackQuery):
    notification_id = call.data.split('_')[2]
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='Удалить', callback_data=f"delete-notification_{notification_id}"))
    await call.message.edit_reply_markup(keyboard)
    await call.answer()


# Обработка подтверждения удаления Уведомления
@dp.callback_query_handler(Text(startswith="yes_delete"))
async def yes_delete_notification(call: types.CallbackQuery):
    delete_notification(notification_id=call.data.split('_')[2])
    await call.message.answer(text="Уведомление удалено", reply_markup=standard_keyboard(call.from_user['id']))
    await call.message.delete()
    await call.answer()
########################################################################################################################


########################################################################################################################
# Обработка команды Тех. Поддержка
@dp.message_handler(text='Тех. Поддержка')
async def cmd_support(message: types.Message, state: FSMContext):
    # await message.answer("Тех. Поддержка", reply_markup=standard_keyboard(message.from_user['id']))
    # await message.delete()
    await message.answer("Тех. Поддержка", reply_markup=support_keyboard())
########################################################################################################################


########################################################################################################################
# АДМИН ПАНЕЛЬ
########################################################################################################################
# Обработка команды Администрирование
@dp.message_handler(text='Администрирование')
async def admin_mode(message: types.Message, state: FSMContext):
    if message.from_user['id'] in admins:
        await States.administrating.set()
        await message.answer("Панель администратора", reply_markup=admin_keyboard())


@dp.message_handler(Text(equals='назад', ignore_case=True), state=States.administrating)
async def cancel_handler(message: types.Message, state: FSMContext):
    await States.administrating.set()
    await message.answer("Панель администратора", reply_markup=admin_keyboard())
########################################################################################################################


########################################################################################################################
# Обработка команды админ Выводы
@dp.message_handler(text='Выводы', state=States.administrating)
async def admin_withdraws(message: types.Message, state: FSMContext):
    await message.answer("Выводы:", reply_markup=admin_keyboard())
    await message.answer("Нет активных выводов:", reply_markup=admin_keyboard())
########################################################################################################################


########################################################################################################################
# Обработка команды админ Промокоды
@dp.message_handler(text='Промокоды', state=States.administrating)
async def admin_promocodes(message: types.Message, state: FSMContext):
    await message.answer("Меню промокодов", reply_markup=promocodes_keyboard())


# Обработка команды админ Создать промокод, ввод имени промокода
@dp.message_handler(text='Создать промокод', state=States.administrating)
async def admin_promocodes_create(message: types.Message, state: FSMContext):
    await States.creating_promocode_name.set()
    await message.answer("Введите название промокода", reply_markup=cancel_keyboard())


# Обработка команды админ Создать промокод, ввод суммы промокода
@dp.message_handler(state=States.creating_promocode_name)
async def admin_promocodes_enter_name(message: types.Message, state: FSMContext):
    await States.creating_promocode_sum.set()
    await state.update_data(promocode_name=str(message.text))
    new_promocode_name = str(message.text)
    await message.answer(f"Промокод: {new_promocode_name}\nВведите сумму промокода ($)", reply_markup=cancel_keyboard())


# Обработка команды админ Создать промокод, создание промокода
@dp.message_handler(state=States.creating_promocode_sum)
async def admin_promocodes_enter_sum(message: types.Message, state: FSMContext):
    fsm_data = await state.get_data()
    new_promocode_name = fsm_data.get("promocode_name")
    try:
        amount = float(message.text)
        if amount > 0:
            await States.administrating.set()
            promocode = {"promocode_id": get_last_promocode_id() + 1, "promocode_name": new_promocode_name,
                         "promocode_sum": message.text}
            create_promocode(promocode=promocode)
            await message.answer(f"Промокод {new_promocode_name} на сумму {amount}$ успешно создан", reply_markup=promocodes_keyboard())
        else:
            await message.answer("Сумма промокода введена неверно, введите число еще раз",
                                 reply_markup=cancel_keyboard())
    except Exception as e:
        await message.answer("Сумма промокода введена неверно, введите число еще раз",
                             reply_markup=cancel_keyboard())


# Обработка команды админ Созданные промокоды
@dp.message_handler(text='Созданные промокоды', state=States.administrating)
async def admin_promocodes_all(message: types.Message, state: FSMContext):
    promocodes = get_all_promocodes()
    if promocodes:
        await message.answer("Созданные промокоды:", reply_markup=promocodes_keyboard())
        for promocode in promocodes:
            keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=1)
            keyboard.add(types.InlineKeyboardButton(text='Удалить', callback_data=f"promocode-delete_{promocode['promocode_id']}"))
            text = str(promocode['promocode_name']) + " на $" + str(promocode['promocode_sum'])
            await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("Активных промокодов нет", reply_markup=promocodes_keyboard())


# Обработка удаления Промокода
@dp.callback_query_handler(Text(startswith="promocode-delete"), state=States.administrating)
async def delete_promocodes(call: types.CallbackQuery):
    promocode_id = call.data.split('_')[1]
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.InlineKeyboardButton(text='Да', callback_data=f"yes-promocode-delete_{promocode_id}"),
                 types.InlineKeyboardButton(text='Нет', callback_data=f"no-promocode-delete_{promocode_id}"))
    await call.message.edit_reply_markup(keyboard)
    await call.answer()


# Обработка отмены удаления Промокода
@dp.callback_query_handler(Text(startswith="no-promocode-delete"), state=States.administrating)
async def no_delete_promocode(call: types.CallbackQuery):
    promocode_id = call.data.split('_')[1]
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='Удалить', callback_data=f"promocode-delete_{promocode_id}"))
    await call.message.edit_reply_markup(keyboard)
    await call.answer()


# Обработка подтверждения удаления Промокода
@dp.callback_query_handler(Text(startswith="yes-promocode-delete"), state=States.administrating)
async def yes_delete_promocode(call: types.CallbackQuery):
    delete_promocode(promocode_id=call.data.split('_')[1])
    await call.message.delete()
    await call.answer()
########################################################################################################################


########################################################################################################################
# Обработка команды админ Реф. ссылки
@dp.message_handler(text='Реф. ссылки', state=States.administrating)
async def admin_ref_links(message: types.Message, state: FSMContext):
    await message.answer("Меню реферальных ссылок", reply_markup=ref_links_keyboard())


# Обработка команды админ Создать реф. ссылку, ввод названия рекламного канала
@dp.message_handler(text='Создать реф. ссылку', state=States.administrating)
async def admin_ref_links_create(message: types.Message, state: FSMContext):
    await States.creating_ref_link.set()
    await message.answer("Введите название рекламного канала", reply_markup=cancel_keyboard())


# Обработка команды админ Создать реф. ссылку, успешно
@dp.message_handler(state=States.creating_ref_link)
async def admin_ref_links_create_successful(message: types.Message, state: FSMContext):
    ref_link_name = str(message.text)
    create_ref_link(ref_link_name=ref_link_name)
    await States.administrating.set()
    await message.answer(f"Реферальная ссылка для рекламного канала: {ref_link_name}:"
                         f"\nhttps://t.me/{bot_name}?start={ref_link_name}", reply_markup=ref_links_keyboard())


# Обработка команды админ Созданные реф ссылки
@dp.message_handler(text='Созданные реф. ссылки', state=States.administrating)
async def admin_ref_links_all(message: types.Message, state: FSMContext):
    ref_links = get_ref_links()
    if ref_links:
        await message.answer("Созданные реф. ссылки:", reply_markup=ref_links_keyboard())
        for ref_link in ref_links:
            keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=1)
            keyboard.add(types.InlineKeyboardButton(text='Удалить', callback_data=f"ref_link_delete_{ref_link['ref_link_id']}"))
            text = f"{ref_link['ref_link_name']}: {ref_link['ref_link_stats']} переходов\nСсылка: {ref_link['ref_link_link']}"
            await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("Нет активных реферальных ссылок", reply_markup=ref_links_keyboard())


# Обработка удаления Реф ссылки
@dp.callback_query_handler(Text(startswith="ref_link_delete"), state=States.administrating)
async def delete_ref_links(call: types.CallbackQuery):
    ref_link_id = call.data.split('_')[3]
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.InlineKeyboardButton(text='Да', callback_data=f"yes_ref_link_delete_{ref_link_id}"),
                 types.InlineKeyboardButton(text='Нет', callback_data=f"no_ref_link_delete_{ref_link_id}"))
    await call.message.edit_reply_markup(keyboard)
    await call.answer()


# Обработка отмены удаления реф ссылки
@dp.callback_query_handler(Text(startswith="no_ref_link_delete"), state=States.administrating)
async def no_delete_ref_link(call: types.CallbackQuery):
    ref_link_id = call.data.split('_')[4]
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='Удалить', callback_data=f"ref_link_delete_{ref_link_id}"))
    await call.message.edit_reply_markup(keyboard)
    await call.answer()


# Обработка подтверждения удаления реф ссылки
@dp.callback_query_handler(Text(startswith="yes_ref_link_delete"), state=States.administrating)
async def yes_delete_ref_link(call: types.CallbackQuery):
    delete_ref_link(ref_link_id=call.data.split('_')[4])
    await call.message.delete()
    await call.answer()
########################################################################################################################


########################################################################################################################
# Обработка команды админ Рассылки
@dp.message_handler(text='Рассылки', state=States.administrating)
async def admin_mailings(message: types.Message, state: FSMContext):
    await message.answer("Меню рассылок", reply_markup=mailing_keyboard())


# Обработка команды админ Создать рассылку
@dp.message_handler(text='Создать рассылку', state=States.administrating)
async def admin_mailings_create(message: types.Message, state: FSMContext):
    await States.entering_mailing_text.set()
    await message.answer("Введите текст рассылки", reply_markup=cancel_keyboard())


# Обработка ввода текста рассылки
@dp.message_handler(state=States.entering_mailing_text)
async def admin_mailings_text(message: types.Message, state: FSMContext):
    await States.sending_mailing_file.set()
    # Сохраняем текст новой рассылки
    await state.update_data(mailing_text=str(message.text))
    await message.answer("Вставьте фото / видео / gif.\nЕсли рассылка без медиа файлов, нажмите кнопку на панели",
                         reply_markup=mailing_media_keyboard())


# Обработка загрузки файла для рассылки
# @dp.message_handler(content_types=[types.ContentType.VIDEO], state=States.sending_mailing_file)
# @dp.message_handler(content_types=[types.ContentType.ANIMATION], state=States.sending_mailing_file)
# @dp.message_handler(content_types=[types.ContentType.PHOTO], state=States.sending_mailing_file)
@dp.message_handler(state=States.sending_mailing_file)
async def admin_mailings_file(message: types.Message, state: FSMContext):
    await States.administrating.set()
    fsm_data = await state.get_data()
    mailing_text = fsm_data.get('mailing_text')
    if message.text != "Нет медиафайлов":
        if message.content_type == 'photo':
            mailing_file_type = 'photo'
            mailing_file_id = message.photo[-1]['file_id']
            await message.answer_photo(mailing_file_id)
        elif message.content_type == 'video':
            mailing_file_type = 'video'
            mailing_file_id = message.video['file_id']
            await message.answer_video(mailing_file_id)
        elif message.content_type == 'animation':
            mailing_file_type = 'animation'
            mailing_file_id = message.animation['file_id']
            await message.answer_animation(mailing_file_id)
        else:
            await message.answer(f"Вставьте фото / видео / gif.\nЕсли рассылка без медиа файлов, нажмите кнопку на панели",
                                 reply_markup=mailing_media_keyboard())
            return
    else:
        mailing_file_type = None
        mailing_file_id = None
    # Создаем рассылку с присланным текстом и файлом
    mailing = {
        "mailing_id": get_last_mailing_id() + 1,
        "mailing_text": mailing_text,
        "mailing_date": None,
        "mailing_file_id": mailing_file_id,
        "mailing_file_type": mailing_file_type,
        "mailing_status": "WAITING"
    }
    create_mailing(mailing)
    await message.answer(f"{mailing['mailing_text']}", reply_markup=mailing_keyboard())
    await message.answer(f"Создана рассылка {mailing['mailing_id']}. Все верно?",
                         reply_markup=mailing_inline_keyboard(mailing))


# Обработка команды админ Созданные рассылки
@dp.message_handler(text='Созданные рассылки', state=States.administrating)
async def admin_mailings_view(message: types.Message, state: FSMContext):
    mailings = get_mailings_to_send()
    if mailings:
        await message.answer("Имеющиеся рассылки:", reply_markup=mailing_keyboard())
        for mailing in mailings:
            post_date = mailing['mailing_date'] if mailing['mailing_date'] else "*нет даты*"
            await message.answer(f"Рассылка {mailing['mailing_id']} назначена на {post_date}:")
            if mailing["mailing_file_type"] == "video":
                await message.answer_video(mailing['mailing_file_id'])
            elif mailing["mailing_file_type"] == "photo":
                await message.answer_photo(mailing['mailing_file_id'])
            elif mailing["mailing_file_type"] == "animation":
                await message.answer_animation(mailing['mailing_file_id'])
            await message.answer(mailing['mailing_text'], reply_markup=mailing_inline_keyboard(mailing))
    else:
        await message.answer("Нет рассылок", reply_markup=mailing_keyboard())


# Обработка команды админ Редактировать дату рассылкы
@dp.callback_query_handler(Text(startswith="mailing-edit"), state=States.administrating)
async def admin_mailing_edit(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(mailing_id=call.data.split('_')[1])
    await States.entering_mailing_date.set()
    await call.message.answer(f"Введите дату публикации рассылки в формате ГГГГ-ММ-ДД ЧЧ:ММ",
                              reply_markup=cancel_keyboard())
    await call.answer()


# Обработка команды админ Ввод даты рассылки
@dp.message_handler(state=States.entering_mailing_date)
async def admin_mailings_date(message: types.Message, state: FSMContext):
    try:
        post_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        if post_time > datetime.utcnow():
            await States.administrating.set()
            fsm_data = await state.get_data()
            mailing_id = fsm_data.get("mailing_id")
            mailing = get_mailing(mailing_id)
            mailing['mailing_date'] = message.text
            update_mailing(mailing=mailing)
            await message.answer(f"Рассылка {mailing['mailing_id']} назначена на {mailing['mailing_date']}",
                                 reply_markup=mailing_keyboard())
        else:
            await message.answer(f"Указанное время уже прошло, задайте новое в формате ГГГГ-ММ-ДД ЧЧ:ММ",
                                 reply_markup=cancel_keyboard())
    except Exception as e:
        await message.answer(f"Введите дату публикации рассылки в формате ГГГГ-ММ-ДД ЧЧ:ММ",
                             reply_markup=cancel_keyboard())


# Обработка команды админ Удалить рассылку
@dp.callback_query_handler(Text(startswith="mailing-delete"), state=States.administrating)
async def admin_mailing_delete(call: types.CallbackQuery, state: FSMContext):
    mailing = get_mailing(mailing_id=call.data.split('_')[1])
    delete_mailing(mailing=mailing)
    await call.message.answer(f"Удалена рассылка {mailing['mailing_id']}, назначенная на {mailing['mailing_date']}.")
    await call.answer()


########################################################################################################################


########################################################################################################################
# Обработка команды админ Заблокировать
@dp.message_handler(text='Заблокировать', state=States.administrating)
async def admin_block(message: types.Message, state: FSMContext):
    await States.admin_blocking.set()
    await message.answer("Введите @username или ID", reply_markup=cancel_keyboard())


# Обработка команды админ Заблокировать?
# Не найдет пользователя в бд, если после регистрации он сменил username!!!!!
@dp.message_handler(state=States.admin_blocking)
async def admin_block_ask(message: types.Message, state: FSMContext):
    user = get_user(message.text)
    if user:
        if user['user_id'] in blocked_users:
            await message.answer(f"Пользователь {user['user_name']} уже заблокирован. Введите другой @username или ID", reply_markup=cancel_keyboard())
        else:
            keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=2)
            keyboard.add(types.InlineKeyboardButton(text='Да', callback_data=f"yes_block_{user['user_id']}"),
                         types.InlineKeyboardButton(text='Нет', callback_data=f"no_block_{user['user_id']}"))
            await message.answer(f"Заблокировать пользователя {user['user_name']}?", reply_markup=keyboard)
    else:
        await message.answer("Нет такого пользователя в базе данных. Введите другой @username или ID", reply_markup=cancel_keyboard())


# Обработка отмены Блокировки пользователя
@dp.callback_query_handler(Text(startswith="no_block"), state=States.admin_blocking)
async def no_block_user(call: types.CallbackQuery, state: FSMContext):
    await States.administrating.set()
    await call.message.answer("Блокировка отменена", reply_markup=admin_keyboard())
    await call.answer()


# Обработка успешной Блокировки пользователя
@dp.callback_query_handler(Text(startswith="yes_block"), state=States.admin_blocking)
async def yes_block_user(call: types.CallbackQuery, state: FSMContext):
    user = get_user(call.data.split('_')[2])
    block_user(user=user)
    await States.administrating.set()
    await call.message.answer(f"Пользователь {user['user_name']} успешно заблокирован", reply_markup=admin_keyboard())
    await call.answer()
########################################################################################################################


########################################################################################################################
# Обработка команды админ Статистика
@dp.message_handler(text='Статистика', state=States.administrating)
async def admin_stat(message: types.Message, state: FSMContext):
    date = str(datetime.utcnow()-timedelta(days=1))[:10]
    stats = get_platform_statistics(date)
    if stats:
        await message.answer(platform_stat_message(stats), reply_markup=statistics_keyboard())
    else:
        await message.answer("Меню статистики", reply_markup=statistics_keyboard())


# Обработка команды админ Платформа по дням
@dp.message_handler(text='Платформа по дням', state=States.administrating)
async def admin_stat_platform(message: types.Message, state: FSMContext):
    await States.entering_date.set()
    await message.answer("Чтобы узнать статистику платформы в конкретный день, введите дату в формате ГГГГ-ММ-ДД",
                         reply_markup=cancel_keyboard())


# Обработка админ вводит дату для проверки статистики платформы
@dp.message_handler(state=States.entering_date)
async def admin_stat_platform(message: types.Message, state: FSMContext):
    await States.administrating.set()
    stats = get_platform_statistics(date=message.text)
    if stats:
        await message.answer(platform_stat_message(stats),
                             reply_markup=statistics_keyboard())
    else:
        await message.answer("Нет статистики на заданную дату, или дата введена неверно",
                             reply_markup=statistics_keyboard())


# Обработка команды админ Пользователи
@dp.message_handler(text='Пользователи', state=States.administrating)
async def admin_stat_user_1(message: types.Message, state: FSMContext):
    users = get_all_users()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for user in users:
        keyboard.add(types.InlineKeyboardButton(text=f'Пользователь {user[0]}', callback_data=f'stat_{user[0]}'))
    await message.answer("Все пользователи:", reply_markup=keyboard)


# Обработка команды админ Статистика пользователя
@dp.callback_query_handler(Text(startswith="stat_"), state=States.administrating)
async def admin_stat_user_2(call: types.CallbackQuery, state: FSMContext):
    user = get_user(int(call.data.split("_")[1]))

    if user:
        await call.message.answer(user_stat_message(user=user), reply_markup=admin_keyboard())
    else:
        await call.message.answer("Что-то пошло не так", reply_markup=admin_keyboard())
    await call.answer()
########################################################################################################################


# Общие команды
########################################################################################################################
@dp.errors_handler(exception=BotBlocked)
async def error_bot_blocked(update: types.Update, exception: BotBlocked):
    # Update: объект события от Telegram. Exception: объект исключения
    # Здесь можно как-то обработать блокировку, например, удалить пользователя из БД
    print(f"Меня заблокировал пользователь!\nСообщение: {update}\nОшибка: {exception}")

    # Такой хэндлер должен всегда возвращать True,
    # если дальнейшая обработка не требуется.
    return True


if __name__ == "__main__":
    scheduler.start()
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)