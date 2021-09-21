# from coinbase.wallet.client import Client
from coinbase_commerce.client import Client
from bot.config import COINBASE_API_KEY, bot_link
from datetime import datetime
from bot.db_service import create_deposit
import random
import requests


API_KEY = COINBASE_API_KEY
client = Client(api_key=API_KEY)


def create_coinbase_payment_link(user_id, amount):
    """
    Creating Charge type payment
    :param user_id: int
    :param amount: float
    :return: deposit link — str
    """
    charge = client.charge.create(name='Crypto Spin Bot',
                                  description='Платеж может обрабатываться некоторое время',
                                  pricing_type='fixed_price',
                                  local_price={
                                      "amount": f"{amount}",
                                      "currency": "USD"
                                  },
                                  metadata={
                                      "user_id": f"{user_id}"
                                  },
                                  redirect_url=bot_link,
                                  cancel_url=bot_link)
    # print(charge)
    deposit_id = charge['id']
    deposit_link = charge['hosted_url']
    create_deposit(deposit_id=deposit_id, user_id=user_id, amount=amount, link=deposit_link, deposit_type="COINBASE")
    return deposit_link


def check_coinbase_payment_status(deposit):
    """
    Проверяем платеж платформы Coinbase
    deposit = {
        'deposit_id': payment[0],
        'user_id': payment[1],
        'amount': payment[2],
        'link': payment[3],
        'status': payment[4],
        'deposit_type': payment[5],
        'date': payment[6],
        }
    :param deposit:
    :return:
    """
    charge = client.charge.retrieve("2b4e1c21-fb70-4b0a-bc4b-4cab7648fa10")
    # print(charge)
    status = charge['timeline'][-1]['status']
    return status


# print(create_coinbase_payment_link(330639572, "12.00"))
deposit = {'deposit_id': "2b4e1c21-fb70-4b0a-bc4b-4cab7648fa10",
           'user_id': 330639572,
           'amount': 12.00,
           'link': " ",
           'status': "NEW",
           'deposit_type': "COINBASE",
           'date': ""
           }

