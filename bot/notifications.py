def start_notification(user_name):
    return f"Приветствуем тебя, {user_name}"


def deposit_success_notification(amount: float):
    return f"Ваш баланс пополнен на {amount}$"


def referral_deposit_notification(user_name: str, amount: float):
    return f"Ваш реферал {user_name} пополнил счет на {amount}. Ваш счет пополнен на {amount*0.1}."
