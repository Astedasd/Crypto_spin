from aiogram import types
from aiogram.utils.markdown import hbold
from db_service import get_new_notifications_number
from config import admins, SPIN_TEXT


def start_keyboard():
    keyboard_1 = types.InlineKeyboardMarkup(row_width=1)
    keyboard_1.add(types.InlineKeyboardButton(text='Ознакомиться 👀', url='https://bit.ly/3vuvQb8'))
    keyboard_2 = types.InlineKeyboardMarkup(row_width=1)
    keyboard_2.add(types.InlineKeyboardButton(text='Я ознакомлен (-а), мне есть 18 лет 🔞', callback_data='ready_to_start'))
    return keyboard_1, keyboard_2


def cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(types.KeyboardButton(text='Отмена'))
    return keyboard


def standard_keyboard(user_id):
    # n = количество непрочитанных уведомлений
    n = get_new_notifications_number(user_id=user_id)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ('Игры', 'Баланс', f'Уведомления ({n})', 'Тех. Поддержка')
    keyboard.add(*(types.KeyboardButton(text) for text in buttons))
    if user_id in admins:
        keyboard.add(types.KeyboardButton(text='Администрирование'))
    return keyboard


def balance_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='Пополнить', callback_data='deposit'))
    keyboard.add(types.InlineKeyboardButton(text='Рефералы', callback_data='referrals'))
    keyboard.add(types.InlineKeyboardButton(text='Активировать промокод', callback_data='activate_promocode'))
    keyboard.add(types.InlineKeyboardButton(text='Вывести', callback_data='withdraw'))
    return keyboard


def support_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='F.A.Q.', url='https://bit.ly/3xvlDxc'))
    keyboard.add(types.InlineKeyboardButton(text='Админ', url='https://t.me/Crypto_Spin_Admin'))
    keyboard.add(types.InlineKeyboardButton(text='Реклама', url='https://t.me/Crypto_Spin_Adv'))
    keyboard.add(types.InlineKeyboardButton(text='Наш Telegram канал', url='https://t.me/Crypto_Spin_Official'))
    keyboard.add(types.InlineKeyboardButton(text='Закрытый канал', url='https://t.me/joinchat/i0cBUMHENjRiODAy'))
    return keyboard


def admin_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ('Выводы', 'Промокоды', 'Реф. ссылки', 'Рассылки', 'Заблокировать', 'Статистика', 'Константы', 'Выход')
    keyboard.add(*(types.KeyboardButton(text) for text in buttons))
    return keyboard


def statistics_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    buttons = ('Платформа по дням', 'Пользователи', 'Назад')
    keyboard.add(*(types.KeyboardButton(text) for text in buttons))
    return keyboard


def mailing_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    buttons = ('Создать рассылку', 'Созданные рассылки', 'Назад')
    keyboard.add(*(types.KeyboardButton(text) for text in buttons))
    return keyboard


def mailing_media_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    buttons = ('Нет медиафайлов', 'Отмена')
    keyboard.add(*(types.KeyboardButton(text) for text in buttons))
    return keyboard


def mailing_inline_keyboard(mailing):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton(text='Редактировать дату', callback_data=f"mailing-edit_{mailing['mailing_id']}")
    # btn2 = types.InlineKeyboardButton(text='Редактировать', callback_data=f"mailing-edit_{mailing['mailing_id']}")
    btn3 = types.InlineKeyboardButton(text='Удалить', callback_data=f"mailing-delete_{mailing['mailing_id']}")
    keyboard.row(btn1, btn3)
    # keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='play_joe'))
    return keyboard


def platform_stat_message(stats):
    text = f"Дата: {stats['date']}\n" \
           f"Баланс: {stats['balance']}$\n" \
           f"__________\n" \
           f"Поступления: {stats['deposits_sum']}$\n" \
           f"N поступлений:{stats['deposits_number']}\n" \
           f"Средний чек: {stats['deposits_average']}$\n" \
           f"Выводы: {stats['withdraws_sum']}$\n" \
           f"N выводов: {stats['withdraws_number']}\n" \
           f"Средний чек: {stats['withdraws_average']}$\n" \
           f"Чистая прибыль: {stats['net_profit']}$\n" \
           f"__________\n" \
           f"Пользователей: {stats['users']}\n" \
           f"Регистраций: {stats['registrations_number']}\n" \
           f"Удалений: {stats['deletes_number']}\n" \
           f"Новых пользователей: {stats['new_users']}\n" \
           f"Действий в боте: {stats['actions_number']}\n" \
           f"Активных пользователей: {stats['active_users']}\n"
    return text


def user_stat_message(user):
    text = f"Пользователь {user['user_name']}:\n" \
           f"ID: {user['user_id']}\n" \
           f"Баланс: {user['balance']}$\n" \
           f"Страховка: {user['insurance']}$\n" \
           f"___________\n" \
           f"Пополнил сумму: {user['deposit_total']}$\n" \
           f"Вывел сумму: {user['withdraw_total']}$\n" \
           f"___________\n" \
           f"Кол-во рефералов: {user['referrals']}\n" \
           f"Сумма бонусов от рефералов: {user['referral_bonus']}$\n" \
           f"Реферальный код: {user['referral_code']}\n" \
           f"___________\n" \
           f"Зарегистрирован: {user['registration_date']}\n"
    return text


def promocodes_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ('Создать промокод', 'Созданные промокоды', 'Назад')
    keyboard.add(*(types.KeyboardButton(text) for text in buttons))
    return keyboard


def channels_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ('Создать реф. ссылку', 'Созданные реф. ссылки', 'Назад')
    keyboard.add(*(types.KeyboardButton(text) for text in buttons))
    return keyboard


def deposit_method_keyboard(user_id: int, amount: float):
    """

    :param user_id: int
    :param amount: float
    :return: keyboard
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='QIWI ($/₽)', callback_data=f'deposit_{user_id}_qiwi_{amount}'))
    keyboard.add(types.InlineKeyboardButton(text='Крипта', callback_data=f'deposit_{user_id}_crypto_{amount}'))
    return keyboard


def withdraw_method_keyboard(user_id: int, amount: float):
    """

    :param user_id: int
    :param amount: float
    :return: keyboard
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='VISA/MasterCard', callback_data=f'withdraw_{user_id}_card_{amount}'))
    keyboard.add(types.InlineKeyboardButton(text='Крипта', callback_data=f'crypto-withdraw_{user_id}_{amount}'))
    return keyboard


def crypto_withdraw_keyboard(user_id: int, amount: float):
    # BTC, ETH, USDC, DAI, BCH, LTC, DOGE
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='BTC', callback_data=f'withdraw_{user_id}_btc_{amount}'))
    keyboard.add(types.InlineKeyboardButton(text='ETH', callback_data=f'withdraw_{user_id}_eth_{amount}'))
    keyboard.add(types.InlineKeyboardButton(text='USDC', callback_data=f'withdraw_{user_id}_usdc_{amount}'))
    keyboard.add(types.InlineKeyboardButton(text='DAI', callback_data=f'withdraw_{user_id}_dai_{amount}'))
    keyboard.add(types.InlineKeyboardButton(text='BCH', callback_data=f'withdraw_{user_id}_bch_{amount}'))
    keyboard.add(types.InlineKeyboardButton(text='LTC', callback_data=f'withdraw_{user_id}_ltc_{amount}'))
    keyboard.add(types.InlineKeyboardButton(text='DOGE', callback_data=f'withdraw_{user_id}_doge_{amount}'))
    return keyboard


def withdraw_accept_keyboard(withdraw_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton(text='Подтвердить', callback_data=f'accept-withdraw-yes_{withdraw_id}')
    btn2 = types.InlineKeyboardButton(text='Отменить', callback_data=f'accept-withdraw-no_{withdraw_id}')
    keyboard.row(btn1, btn2)
    return keyboard


def games_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text='Однорукий Джо', callback_data='play_joe'))
    return keyboard


def joe_keyboard(stake):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=False, row_width=3)
    keyboard.add(types.KeyboardButton(text=SPIN_TEXT))
    buttons = ('⬅', f'Ставка ({stake})', '➡')
    keyboard.add(*(types.KeyboardButton(text) for text in buttons))
    keyboard.add(types.KeyboardButton(text='Max ставка'))
    keyboard.add(types.KeyboardButton(text='Выход'))
    return keyboard


def stake_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton(text='100$', callback_data='stake_100')
    btn2 = types.InlineKeyboardButton(text='75$', callback_data='stake_75')
    btn3 = types.InlineKeyboardButton(text='50$', callback_data='stake_50')
    btn4 = types.InlineKeyboardButton(text='25$', callback_data='stake_25')
    btn5 = types.InlineKeyboardButton(text='10$', callback_data='stake_10')
    btn6 = types.InlineKeyboardButton(text='5$', callback_data='stake_5')
    btn7 = types.InlineKeyboardButton(text='0.75$', callback_data='stake_0.75')
    btn8 = types.InlineKeyboardButton(text='0.5$', callback_data='stake_0.5')
    btn9 = types.InlineKeyboardButton(text='0.25$', callback_data='stake_0.25')
    btn10 = types.InlineKeyboardButton(text='0.1$', callback_data='stake_0.1')
    btn11 = types.InlineKeyboardButton(text='0.05$', callback_data='stake_0.05')
    btn12 = types.InlineKeyboardButton(text='0.01$', callback_data='stake_0.01')
    keyboard.row(btn1, btn2, btn3)
    keyboard.row(btn4, btn5, btn6)
    keyboard.row(btn7, btn8, btn9)
    keyboard.row(btn10, btn11, btn12)
    # keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='play_joe'))
    return keyboard


def spin_keyboard():
    # noinspection PyTypeChecker
    return types.ReplyKeyboardMarkup([["🎰"]], resize_keyboard=True)


def joe_message(balance, promo_balance, result, insurance):
    return f"{hbold('Ваш счёт: ')}{balance}$\n{hbold('Баланс с промокодов: ')}{promo_balance}$\n" \
           f"{hbold('Результат: ')}{result}$\n{hbold('Страховка: ')}{insurance}$\n" \
           f"________________\n" \
           f"{hbold('Bar Bar Bar')} – {hbold('x5')}\n" \
           f"7️⃣ 7️⃣ 7️⃣ – {hbold('x3')}\n" \
           f"🍋🍋🍋  – {hbold('x2')}\n" \
           f"🍒🍒🍒 – {hbold('x2')}  \n"
