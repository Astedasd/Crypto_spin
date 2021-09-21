import requests
import json
from bot.config import public_key, secret_key, dollar
from datetime import datetime, timedelta
import time
from bot.db_service import create_deposit
import random


# Проверяем баланс Qiwi
def qiwi_balance(login, api_access_token):
    s = requests.Session()
    s.headers['Accept'] = 'application/json'
    s.headers['authorization'] = 'Bearer ' + api_access_token
    b = s.get('https://edge.qiwi.com/funding-sources/v2/persons/' + login + '/accounts')
    print(b.json())


# История платежей - последние и следующие n платежей
def payment_history_last(my_login, api_access_token):
    s = requests.Session()
    s.headers['authorization'] = 'Bearer ' + api_access_token
    #parameters = {'rows': rows_num, 'nextTxnId': next_TxnId, 'nextTxnDate': next_TxnDate}
    parameters = {'rows': 10, 'operation': 'IN'}
    h = s.get('https://edge.qiwi.com/payment-history/v2/persons/' + my_login + '/payments', params=parameters)
    return h.json()


# Создаем платеж, записываем в бд и возвращаем ссылку для оплаты
def create_qiwi_payment_link(user_id: int, amount: float):
    # Формируем ID платежа
    sep = '000'
    id_form = (str(user_id), str(random.randint(0, 100000)))
    payment_id = sep.join(id_form)
    amount = round(float(amount), 2)
    dollar_amount = round(float(amount * dollar), 2)
    print(amount)
    # Формируем запрос
    payment_link = f"https://oplata.qiwi.com/create?publicKey=" \
                   f"{public_key}&billId={payment_id}&amount={dollar_amount}&account={user_id}&customFields%5BthemeCode%5D=Valentyn-AIGYYGzVSH"

    # Заносим платеж в бд
    create_deposit(deposit_id=payment_id, user_id=user_id, amount=amount, link=payment_link, deposit_type="QIWI")
    return payment_link


def check_qiwi_payment_status(deposit):
    """

    :param deposit:
    :return:
    """
    s = requests.Session()
    s.headers['Authorization'] = 'Bearer ' + secret_key
    s.headers['Accept'] = 'application/json'
    h = s.get(f"https://api.qiwi.com/partner/bill/v1/bills/{deposit['deposit_id']}")
    answer = h.json()
    # Если счет не создан
    if str(answer).find('Invoice not found') != -1:
        return 'WAITING'
    else:
        return answer['status']['value']
