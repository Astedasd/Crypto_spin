import requests
import json
from bot.config import public_key, secret_key, dollar
# from bot.config import api_access_token
from datetime import datetime, timedelta
import time
from bot.db_service import create_deposit, get_withdraw
import random

"""
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
"""


# Создаем платеж, записываем в бд и возвращаем ссылку для оплаты
def create_qiwi_payment_link(user_id: int, amount: float):
    # Формируем ID платежа
    sep = '000'
    id_form = (str(user_id), str(random.randint(0, 100000)))
    payment_id = sep.join(id_form)
    amount = round(float(amount), 2)
    dollar_amount = round(float(amount * dollar), 2)
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


def get_dollar_rub(api_access_token, currency_from, currency_to):
    s = requests.Session()
    s.headers = {'content-type': 'application/json'}
    s.headers['authorization'] = 'Bearer ' + api_access_token
    s.headers['User-Agent'] = 'Android v3.2.0 MKT'
    s.headers['Accept'] = 'application/json'
    res = s.get('https://edge.qiwi.com/sinap/crossRates')

    # все курсы
    rates = res.json()['result']

    # запрошенный курс
    rate = [x for x in rates if x['from'] == currency_from and x['to'] == currency_to]
    if (len(rate) == 0):
        print('No rate for this currencies!')
        return
    else:
        return rate[0]['rate']
    pass


def pay_withdraw(withdraw):
    # payment_data - dictionary with all payment data
    s = requests.Session()
    s.headers['Accept'] = 'application/json'
    s.headers['Content-Type'] = 'application/json'
    s.headers['authorization'] = 'Bearer ' + api_access_token
    postjson = {"id": "", "sum": {"amount": "", "currency": "643"},
                "paymentMethod": {"type": "Account", "accountId": "643"}, "fields": {"account": ""}}
    postjson['id'] = str(int(time.time() * 1000))
    postjson['sum']['amount'] = str(float(withdraw['amount'])*dollar)
    postjson['fields']['account'] = str(withdraw['withdraw_info'])
    if str(withdraw['withdraw_info']).startswith('4'):
        prv_id = '1963'
    elif str(withdraw['withdraw_info']).startswith('5'):
        prv_id = '21013'
    """
    if payment_data.get('prv_id') in ['1960', '21012']:
        postjson['fields']['rem_name'] = payment_data.get('rem_name')
        postjson['fields']['rem_name_f'] = payment_data.get('rem_name_f')
        postjson['fields']['reg_name'] = payment_data.get('reg_name')
        postjson['fields']['reg_name_f'] = payment_data.get('reg_name_f')
        postjson['fields']['rec_city'] = payment_data.get('rec_address')
        postjson['fields']['rec_address'] = payment_data.get('rec_address')
    """

    res = s.post('https://edge.qiwi.com/sinap/api/v2/terms/' + prv_id + '/payments', json=postjson)
    return res.json()
    pass

