import requests
import json
from datetime import datetime


def RealTimeCurrencyExchangeRate(from_currency, to_currency, api_key):
    # base_url variable store base url
    base_url = r"https://www.alphavantage.co/query?function = CURRENCY_EXCHANGE_RATE"

    # main_url variable store complete url
    main_url = base_url + "&from_currency =" + from_currency + "&to_currency =" + to_currency + "&apikey =" + api_key
    # get method of requests module
    # return response object
    req_ob = requests.get(main_url)

    # json method return json format
    # data into python dictionary data type.

    # result contains list of nested dictionaries
    result = req_ob.json()
    print(" Result before parsing the json data :\n", result)

    print("\n After parsing : \n Realtime Currency Exchange Rate for",
          result["Realtime Currency Exchange Rate"]
          ["2. From_Currency Name"], "TO",
          result["Realtime Currency Exchange Rate"]
          ["4. To_Currency Name"], "is",
          result["Realtime Currency Exchange Rate"]
          ['5. Exchange Rate'], to_currency)


# Имя бота
bot_name = "Crypto_Spin_Bot"
bot_link = f"https://t.me/{bot_name}"
BOT_TOKEN = "1770088350:AAEJ3eKwmsmojeRZxWarjTKioZuJ7YAniKo"

# Права администратора
admins = (330639572, 1537126137, 410785491, 1417744142, 333583210)

# Кнопка играть
SPIN_TEXT = "🎰 Крутить"

public_key = "48e7qUxn9T7RyYE1MVZswX1FRSbE6iyCj2gCRwwF3Dnh5XrasNTx3BGPiMsyXQFNKQhvukniQG8RTVhYm3iP4rNgj2WQkfDnCsQsVKXpFgdcS1xy6wrq5ChxRH9VHB87N8hUziFsDMgmMvn5wp7KLSuvqtwpDm6qtLJ9AY9wQgB48QZX7guhihiPET7mD"
secret_key = "eyJ2ZXJzaW9uIjoiUDJQIiwiZGF0YSI6eyJwYXlpbl9tZXJjaGFudF9zaXRlX3VpZCI6IjM3cDQ0ci0wMCIsInVzZXJfaWQiOiI3OTA0MzA5NTg1MCIsInNlY3JldCI6ImJiNmE0YjNjNWZiMGExYmEwODU5ZjYzZTBhMGI0MWU0OTg4ZGU3ZDIxM2M2ZDM3NDRlNjVkMGMxNzE2ZTYzNDEifX0="
dollar = 73.0
api_access_token = "R84796LA6M723U47"


COINBASE_API_KEY = "2db246d3-d58d-4a52-9aaa-421b64bf7874"

# ROFL_VIDEO_ID = "BAACAgIAAxkBAAIqQWFDRGYeUYwsHagnHB9YUf-C6o3AAAL4DQACgkgYSki1Hogj89koIAQ"
ROFL_VIDEO_ID = "BAACAgIAAxkBAAMgYVGnQcYUEyOLxL95ASh0coNdfXEAAlAUAAK3oohKOn3hLQFVy28hBA"
