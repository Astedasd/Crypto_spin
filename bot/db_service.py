import sqlite3
from datetime import datetime, timedelta
from bot.config import bot_name
import random


# Подключение к БД
def connect_db():
    con = sqlite3.connect('crypto_spin_bot.db')
    cur = con.cursor()
    return con, cur


# Команды для бд
def register_user(user_id, user_name):
    # Чекаем регистрацию
    # Если нет в бд, то добавляем и возвращаем True. Если есть в бд, то возвращаем False
    con, cur = connect_db()
    if not get_user(user_id):
        # регистрируем
        balance = insurance = deposit_total = withdraw_total = 0.0
        referral_code = ""
        referrals = 0
        referral_bonus = 0.0
        registration_date = str(datetime.utcnow())[0:19]
        print("Регистрирую пользователя '%s'" % user_id)
        data = (user_id, user_name, balance, insurance, registration_date, deposit_total, withdraw_total, referral_code,
                referrals, referral_bonus)
        cur.execute(f"""INSERT INTO users (user_id, user_name, balance, insurance, registration_date, deposit_total,
                    withdraw_total, referral_code, referrals, referral_bonus) VALUES (?,?,?,?,?,?,?,?,?,?)""", data)
        con.commit()
        con.close()
        return True
    else:
        # уже зарегистрирован
        print(f"Пользователь {user_id} уже зарегистрирован")
        con.close()
        return False


def update_username(user_id, user_name):
    con, cur = connect_db()
    cur.execute(f"""UPDATE users SET user_name = '%s' WHERE user_id = '%s'""" % (user_name, user_id))
    con.commit()
    con.close()


def get_user(user):
    """

    :param user: username или user_id
    :return:
    """
    con, cur = connect_db()
    if type(user) == int:
        cur.execute(f"""SELECT user_id, user_name, balance, insurance, registration_date, deposit_total, withdraw_total,
                        referral_code, referrals, referral_bonus FROM users WHERE user_id = '%s'""" % user)
    else:
        cur.execute(f"""SELECT user_id, user_name, balance, insurance, registration_date, deposit_total, withdraw_total,
                        referral_code, referrals, referral_bonus FROM users WHERE user_name = '%s'""" % user)
    data = cur.fetchone()
    con.close()
    if data:
        user = {
            "user_id": data[0],
            "user_name": data[1],
            "balance": round(data[2], 2),
            "insurance": round(data[3], 2),
            "registration_date": data[4],
            "deposit_total": round(data[5], 2),
            "withdraw_total": round(data[6], 2),
            "referral_code": data[7],
            "referrals": data[8],
            "referral_bonus": round(data[9], 2),
        }
        return user
    else:
        # Если не зарегистрирован в бд,
        # то возвращаем False для проверки регистрации
        return False


def get_all_users():
    con, cur = connect_db()
    cur.execute(f"""SELECT * FROM users""")
    data = cur.fetchall()
    users = []
    if data:
        for user in data:
            users.append({
                "user_id": user[0],
                "user_name": user[1],
                "balance": round(user[2], 2),
                "insurance": round(user[3], 2),
                "registration_date": user[4],
                "deposit_total": round(user[5], 2),
                "withdraw_total": round(user[6], 2),
                "referral_code": user[7],
                "referrals": user[8],
                "referral_bonus": round(user[9], 2),
            })
    return users


def get_referrals(user_id):
    con, cur = connect_db()
    cur.execute(f"""SELECT user_name FROM referrals, users WHERE referrals.user_id = '%s' and users.user_id = referral_id""" % user_id)
    referrals = cur.fetchall()
    con.close()
    if referrals:
        result = []
        for referral in referrals:
            result.append(referral[0])
        return result
    else:
        return False


def get_referrer(user_id):
    con, cur = connect_db()
    cur.execute(f"""SELECT user_id FROM referrals WHERE referral_id = '%s'""" % user_id)
    referrer = cur.fetchone()[0]
    con.close()
    return referrer


def set_referral(user_id: str, referral_id: int):
    """

    :param user_id: str
    :param referral_id: int
    :return:
    """
    con, cur = connect_db()
    data = (user_id, referral_id)
    cur.execute(f"""INSERT INTO referrals (user_id, referral_id) VALUES (?,?)""", data)
    con.commit()
    if user_id.startswith('r'):
        cur.execute(f"""UPDATE channels SET channel_visitors = channel_visitors + 1,
                        channel_registrations = channel_registrations + 1 WHERE channel_code = '%s'""" % user_id)
    else:
        cur.execute(f"""UPDATE users SET referrals = referrals + 1 WHERE user_id = '%s'""" % user_id)
    con.close()


def get_promocode(promocode_name):
    con, cur = connect_db()
    cur.execute(f"""SELECT promocode_name, promocode_sum, promocode_id FROM promocodes WHERE promocode_name = '%s'""" % promocode_name)
    data = cur.fetchone()
    if data:
        promocode = {
            "promocode_name": data[0],
            "promocode_sum": data[1],
            "promocode_id": data[2]
        }
        return promocode
    else:
        return False


def create_promocode(promocode):
    con, cur = connect_db()
    data = (promocode['promocode_id'], promocode['promocode_name'], promocode['promocode_sum'])
    print(f"Создан промокод {promocode['promocode_name']} на ${promocode['promocode_sum']}")
    try:
        cur.execute(f"""INSERT INTO promocodes (promocode_id, promocode_name, promocode_sum) VALUES (?,?,?)""", data)
    except Exception as e:
        pass
    con.commit()
    con.close()


def get_all_promocodes():
    con, cur = connect_db()
    cur.execute(f"""SELECT promocode_id, promocode_name, promocode_sum FROM promocodes""")
    data = cur.fetchall()
    con.close()
    if data:
        promocodes = []
        for line in data:
            promocodes.append({
                'promocode_id': line[0],
                'promocode_name': line[1],
                'promocode_sum': line[2]
                                  })
        return promocodes
    else:
        return False


def get_last_promocode_id():
    con, cur = connect_db()
    cur.execute(f"""SELECT max(promocode_id) FROM promocodes""")
    n = cur.fetchone()[0]
    con.close()
    return n


def delete_promocode(promocode_id):
    con, cur = connect_db()
    print("Удаляю промокод", promocode_id)
    cur.execute(f"""DELETE FROM promocodes WHERE promocode_id = '%s'""" % promocode_id)
    con.commit()
    con.close()


def promocode_activated(user_id, promocode_name):
    con, cur = connect_db()
    cur.execute(
        f"""SELECT promocode_name FROM promocodes_activated WHERE user_id = '%s' AND promocode_name = '%s'""" % (user_id, promocode_name))
    result = cur.fetchone()
    if result:
        return True
    else:
        return False


def activate_promocode(user_id, promocode_name):
    con, cur = connect_db()
    data = (user_id, promocode_name)
    cur.execute(f"""INSERT INTO promocodes_activated (user_id, promocode_name) VALUES (?,?)""", data)
    con.commit()
    con.close()


def update_balance(user_id: int, delta_money: float, delta_insurance: float):
    con, cur = connect_db()
    cur.execute("""SELECT balance, insurance FROM users WHERE user_id = '%s'""" % user_id)
    data = cur.fetchone()
    new_balance = round(data[0], 2) + delta_money
    new_insurance = round(data[1], 2) + delta_insurance
    cur.execute("""UPDATE users SET balance = '%s', insurance = '%s' WHERE user_id='%s'""" % (new_balance, new_insurance, user_id))
    con.commit()
    con.close()


def create_notification(user_id, notification_text):
    con, cur = connect_db()
    cur.execute(f"""SELECT max(notification_id) FROM notifications WHERE user_id = '%s'""" % user_id)
    notification_id = cur.fetchone()[0]
    if notification_id:
        notification_id = int(notification_id) + 1
    else:
        notification_id = int(str(user_id) + "00001")
    notification_date = str(datetime.utcnow())[0:19]
    data = (notification_id, user_id, notification_text, True, notification_date)
    cur.execute(f"""INSERT INTO notifications (notification_id, user_id, notification_text, is_new, notification_date)
                VALUES (?,?,?,?,?)""", data)
    con.commit()
    con.close()
    pass


def get_notifications(user_id):
    con, cur = connect_db()
    cur.execute(f"""SELECT notification_id, notification_text, is_new, notification_date FROM notifications WHERE user_id = '%s'""" % user_id)
    data = cur.fetchall()
    con.close()
    if data:
        notifications = []
        for line in data:
            notifications.append({
                'notification_id': line[0],
                'notification_text': line[1],
                'is_new': line[2],
                'notification_date': line[3]
                                  })
        return notifications
    else:
        return False


def get_new_notifications_number(user_id):
    con, cur = connect_db()
    cur.execute(f"""SELECT COUNT(notification_id) FROM notifications WHERE user_id = '%s'""" % user_id)
    n = cur.fetchone()[0]
    con.close()
    return n


def update_notifications_read(notifications):
    pass


def delete_notification(notification_id):
    con, cur = connect_db()
    cur.execute(f"""DELETE FROM notifications WHERE notification_id = '%s'""" % notification_id)
    con.commit()
    con.close()


def create_mailing(mailing):
    """
    Создает запись рыссылки в таблице рассылок
    :param mailing:
    :return:
    """
    con, cur = connect_db()
    data = (
        mailing['mailing_id'],
        mailing['mailing_text'],
        mailing['mailing_date'],
        mailing['mailing_file_id'],
        mailing['mailing_file_type'],
        mailing['mailing_status']
        )
    cur.execute(f"""INSERT INTO mailings (mailing_id, mailing_text, mailing_date, mailing_file_id, mailing_file_type,
                mailing_status) VALUES (?,?,?,?,?,?)""", data)
    con.commit()
    con.close()


def delete_mailing(mailing):
    con, cur = connect_db()
    cur.execute(f"""DELETE FROM mailings WHERE mailing_id = '%s'""" % mailing['mailing_id'])
    con.commit()
    con.close()


def update_mailing(mailing):
    con, cur = connect_db()
    cur.execute("""UPDATE mailings SET mailing_text = '%s', mailing_date = '%s', mailing_file_id = '%s',
                mailing_file_type = '%s', mailing_status = '%s' WHERE mailing_id='%s'""" %
                (mailing['mailing_text'], mailing['mailing_date'], mailing['mailing_file_id'],
                 mailing['mailing_file_type'], mailing['mailing_status'], mailing['mailing_id']))
    con.commit()
    con.close()
    pass


def get_mailing(mailing_id: int):
    con, cur = connect_db()
    cur.execute(f"""SELECT *  FROM mailings WHERE mailing_id = '%s'""" % mailing_id)
    data = cur.fetchone()
    con.close()
    mailing = {
            "mailing_id": data[0],
            "mailing_text": data[1],
            "mailing_date": data[2],
            "mailing_file_id": data[3],
            "mailing_file_type": data[4],
            "mailing_status": data[5]
            }
    return mailing


def get_last_mailing_id():
    con, cur = connect_db()
    cur.execute(f"""SELECT max(mailing_id)  FROM mailings""")
    mailing_id = cur.fetchone()[0]
    con.close()
    return mailing_id


def get_mailings_to_send():
    con, cur = connect_db()
    cur.execute(f"""SELECT *  FROM mailings WHERE mailing_status = 'WAITING' ORDER BY mailing_date""")
    data = cur.fetchall()
    con.close()
    mailings = []
    if data:
        for mailing in data:
            mailings.append({
                "mailing_id": mailing[0],
                "mailing_text": mailing[1],
                "mailing_date": mailing[2],
                "mailing_file_id": mailing[3],
                "mailing_file_type": mailing[4],
                "mailing_status": mailing[5]
            })
    return mailings


def create_channel(channel_name: str, channel_code: str):
    con, cur = connect_db()
    cur.execute(f"""SELECT max(channel_id) FROM channels""")
    channel_id = cur.fetchone()[0]
    if channel_id:
        channel_id = int(channel_id) + 1
    else:
        channel_id = 1
    data = (channel_id, channel_name, channel_code)
    cur.execute(f"""INSERT INTO channels (channel_id, channel_name, channel_code) VALUES (?,?,?)""", data)
    con.commit()
    con.close()


def delete_channel(channel_id):
    con, cur = connect_db()
    cur.execute(f"""UPDATE channels SET is_deleted = TRUE WHERE channel_id = '%s'""" % channel_id)
    con.commit()
    con.close()


def get_channel(channel_code):
    con, cur = connect_db()
    cur.execute(f"""SELECT * FROM channels WHERE channel_code = '%s'""" % channel_code)
    data = cur.fetchone()
    con.close()
    if data:
        channel = ({
            "channel_name": data[1],
            "channel_code": data[2],
            "channel_visitors": data[3],
            "channel_registrations": data[4],
            "channel_promocode_num": data[5],
            "channel_promocode_sum": data[6],
            "channel_deposits_num": data[7],
            "channel_deposits_sum": data[8],
            "channel_withdraws_num": data[9],
            "channel_withdraws_sum": data[10],
        })
        return channel
    else:
        return False


def update_channel(channel):
    con, cur = connect_db()
    cur.execute(f"""UPDATE channels SET channel_name = '%s', channel_visitors = '%s',
                channel_registrations = '%s', channel_promocode_num = '%s', channel_promocode_sum = '%s',
                channel_deposits_num = '%s', channel_deposits_sum = '%s', channel_withdraws_num = '%s',
                channel_withdraws_sum = '%s'
                WHERE channel_code = '%s'""" % (channel['channel_name'], channel['channel_visitors'],
                                                channel['channel_registrations'], channel['channel_promocode_num'],
                                                channel['channel_promocode_sum'], channel['channel_deposits_num'],
                                                channel['channel_deposits_sum'], channel['channel_withdraws_num'],
                                                channel['channel_withdraws_sum'], channel['channel_code']))
    con.commit()
    con.close()


def get_channels():
    con, cur = connect_db()
    cur.execute(f"""SELECT * FROM channels WHERE is_deleted = FALSE""")
    data = cur.fetchall()
    con.close()
    channels = []
    if data:
        for line in data:
            channels.append({
                'channel_id': line[0],
                'channel_name': line[1],
                'channel_code': line[2],
                'channel_registrations': line[4]
                                  })
        return channels
    else:
        return False


def prepare_channels_stat():
    con, cur = connect_db()
    cur.execute(f"""SELECT * FROM channels""")
    data = cur.fetchall()
    con.close()
    channels = []
    for channel in data:
        channels.append({
            "channel_name": channel[1],
            "channel_code": channel[2],
            "channel_visitors": channel[3],
            "channel_registrations": channel[4],
            "channel_promocode_num": channel[5],
            "channel_promocode_sum": channel[6],
            "channel_deposits_num": channel[7],
            "channel_deposits_sum": channel[8],
            "channel_withdraws_num": channel[9],
            "channel_withdraws_sum": channel[10],
        })
    return channels


def get_blocked_users():
    con, cur = connect_db()
    cur.execute(f"""SELECT user_id FROM blocked_users""")
    data = cur.fetchall()
    con.close()
    if data:
        blocked_users = []
        for line in data:
            blocked_users.append(line[0])
        return blocked_users
    else:
        return False


def block_user(user):
    con, cur = connect_db()
    data = (user['user_id'], user['user_name'])
    cur.execute(f"""INSERT INTO blocked_users (user_id, user_name) VALUES (?,?)""", data)
    con.commit()
    con.close()


def save_action(user_id, action, action_type):
    """

    :param user_id: int
    :param action: str
    :param action_type: REGISTRATION WIN LOSE PROMOCODE BLOCK INSURANCE DEPOSIT WITHDRAW
    :return:
    """
    con, cur = connect_db()
    date = str(datetime.utcnow())[0:19]
    data = (user_id, date, action, action_type)
    cur.execute(f"""INSERT INTO activity (user_id, date, action, action_type) VALUES (?,?,?,?)""", data)
    con.commit()
    con.close()


def create_deposit(deposit_id, user_id, amount, link, deposit_type):
    con, cur = connect_db()
    # date = str(datetime.utcnow())[0:19]
    date = datetime.utcnow()
    status = 'NEW'
    # print(f"Создан платеж {payment_id} на сумму {amount}")
    data = (deposit_id, user_id, amount, link, status, deposit_type, date)
    cur.execute(f"""INSERT INTO deposits (deposit_id, user_id, amount, link, status, deposit_type, date) VALUES (?,?,?,?,?,?,?)""", data)
    con.commit()
    con.close()


def update_deposit_status(deposit, new_status):
    con, cur = connect_db()
    cur.execute("""UPDATE deposits SET status = '%s' WHERE deposit_id='%s'""" % (new_status, deposit['deposit_id']))
    con.commit()
    con.close()
    pass


def get_waiting_deposits():
    # WAITING PAID REJECTED EXPIRED
    con, cur = connect_db()
    cur.execute(f"""SELECT deposit_id, user_id, amount, link, status, deposit_type, date FROM deposits WHERE status = 'WAITING' or status = 'NEW'""")
    result = cur.fetchall()
    con.close()
    if result:
        payments = []
        for payment in result:
            payment = {
                'deposit_id': payment[0],
                'user_id': payment[1],
                'amount': payment[2],
                'link': payment[3],
                'status': payment[4],
                'deposit_type': payment[5],
                'date': payment[6],
            }
            payments.append(payment)
        return payments
    else:
        return None


def create_withdraw(user_id, amount, withdraw_type):
    sep = '000'
    id_form = (str(user_id), str(random.randint(0, 100000)))
    withdraw_id = sep.join(id_form)
    date = datetime.utcnow()
    data = (withdraw_id, user_id, amount, withdraw_type, "WAITING", date, "None")
    con, cur = connect_db()
    cur.execute("""INSERT INTO withdraws (withdraw_id, user_id, amount, withdraw_type, status, date, withdraw_info) VALUES (?,?,?,?,?,?,?)""", data)
    con.commit()
    con.close()
    return withdraw_id


def get_withdraw(withdraw_id):
    con, cur = connect_db()
    cur.execute("""SELECT * FROM withdraws WHERE withdraw_id = '%s'""" % withdraw_id)
    data = cur.fetchone()
    if data:
        withdraw = {
            'withdraw_id': data[0],
            'user_id': data[1],
            'amount': data[2],
            'withdraw_type': data[3],
            'status': data[4],
            'date': data[5],
            'withdraw_info': data[6]
        }
        return withdraw
    else:
        return False


def get_waiting_withdraws():
    con, cur = connect_db()
    cur.execute("""SELECT * FROM withdraws WHERE status =  'WAITING'""")
    data = cur.fetchall()
    withdraws = []
    if data:
        for withdraw in data:
            withdraws.append({
                'withdraw_id': withdraw[0],
                'user_id': withdraw[1],
                'amount': withdraw[2],
                'withdraw_type': withdraw[3],
                'status': withdraw[4],
                'date': withdraw[5],
                'withdraw_info': withdraw[6]
            })
        return withdraws
    else:
        return False


def update_withdraw(withdraw):
    con, cur = connect_db()
    cur.execute("""UPDATE withdraws SET user_id='%s', amount='%s', withdraw_type='%s', status='%s', date='%s',
                withdraw_info='%s' WHERE withdraw_id = '%s'""" % (withdraw['user_id'], withdraw['amount'],
                                                                  withdraw['withdraw_type'], withdraw['status'],
                                                                  withdraw['date'], withdraw['withdraw_info'],
                                                                  withdraw['withdraw_id'],))
    con.commit()
    con.close()


def prepare_daily_stat():
    con, cur = connect_db()
    datetime.today()
    yesterday = str(datetime.utcnow()-timedelta(days=1))[:10]+'%'
    # Считаем депозиты
    cur.execute("""SELECT amount FROM deposits WHERE date LIKE '%s'""" % yesterday)
    deposits = cur.fetchall()
    deposits_sum = 0.0
    deposits_number = 0
    deposits_average = 0.0
    if deposits:
        for deposit in deposits:
            deposits_sum = deposits_sum + deposit[0]
            deposits_number += 1
        deposits_average = round(deposits_sum/deposits_number, 2)
    # Считаем выводы
    cur.execute("""SELECT amount FROM withdraws WHERE date LIKE '%s'""" % yesterday)
    withdraws = cur.fetchall()
    withdraws_sum = 0.0
    withdraws_number = 0
    withdraws_average = 0.0
    if withdraws:
        for withdraw in withdraws:
            withdraws_sum = withdraws_sum + withdraw[0]
            withdraws_number += 1
        withdraws_average = round(withdraws_sum/withdraws_number, 2)
    net_profit = deposits_sum - withdraws_sum
    balance = deposits_sum - withdraws_sum

    # Cчитаем активность пользователей
    cur.execute("""SELECT COUNT(user_id) FROM users""")
    users = cur.fetchone()[0]
    # Количество регистраций
    cur.execute(
        """SELECT COUNT(user_id) FROM activity WHERE action_type = 'REGISTRATION' AND date LIKE '%s'""" % yesterday)
    registrations_number = cur.fetchone()[0]
    # Количество удалений бота
    cur.execute(
        """SELECT COUNT(user_id) FROM activity WHERE action_type = 'DELETE' AND date LIKE '%s'""" % yesterday)
    deletes_number = cur.fetchone()[0]
    new_users = registrations_number-deletes_number
    # Количество действий в боте и количество активных пользователей
    cur.execute(
        """SELECT COUNT(user_id), COUNT (DISTINCT user_id) FROM activity WHERE date LIKE '%s'""" % yesterday)
    data = cur.fetchone()
    actions_number = data[0]
    active_users = data[1]
    date = yesterday[:-1]
    stats = {
        "date": date,
        "balance": balance,
        "deposits_sum": deposits_sum,
        "deposits_number": deposits_number,
        "deposits_average": deposits_average,
        "withdraws_sum": withdraws_sum,
        "withdraws_number": withdraws_number,
        "withdraws_average": withdraws_average,
        "net_profit": net_profit,
        "users": users,
        "registrations_number": registrations_number,
        "deletes_number": deletes_number,
        "new_users": new_users,
        "actions_number": actions_number,
        "active_users": active_users
    }
    # Записываем дневную статистику в таблицу
    data = (date, balance, deposits_sum, deposits_number, deposits_average, withdraws_sum, withdraws_number,
            withdraws_average, net_profit, users, registrations_number, deletes_number, new_users, actions_number,
            active_users)
    cur.execute(f"""INSERT INTO platform_statistics (date, balance, deposits_sum, deposits_number, deposits_average,
                withdraws_sum, withdraws_number, withdraws_average, net_profit, users, registrations_number,
                deletes_number, new_users, actions_number, active_users)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", data)
    con.commit()
    con.close()
    return stats


def get_platform_statistics(date: str):
    con, cur = connect_db()
    cur.execute(
        """SELECT * FROM platform_statistics WHERE date = '%s'""" % date)
    data = cur.fetchone()
    if data:
        stats = {
            "date": data[0],
            "balance": data[1],
            "deposits_sum": data[2],
            "deposits_number": data[3],
            "deposits_average": data[4],
            "withdraws_sum": data[5],
            "withdraws_number": data[6],
            "withdraws_average": data[7],
            "net_profit": data[8],
            "users": data[9],
            "registrations_number": data[10],
            "deletes_number": data[11],
            "new_users": data[12],
            "actions_number": data[13],
            "active_users": data[14]
        }
        return stats
    else:
        return False


def get_admins():
    con, cur = connect_db()
    cur.execute(
        """SELECT * FROM admins""")
    data = cur.fetchall()
    admins = []
    if data:
        for admin in data:
            admins.append({
                "user_id": admin[0],
                "user_name": admin[1]
            })
    return admins


def delete_admin(user_id: int):
    pass


def insert_admin(user_id: int, user_name: str):
    pass


# date = str(datetime.utcnow()-timedelta(days=1))[:10]
# stats = get_platform_statistics(date)
# print(stats)