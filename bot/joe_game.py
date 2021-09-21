from typing import List, Tuple

#           0       1         2        3
casino = ["BAR", "виноград", "лимон", "семь"]
# combo
"""
Bar Bar Bar – Х5
7️⃣ 7️⃣ 7️⃣ – Х3
🍋🍋🍋  – Х2
🍒🍒🍒 – Х2
"""


def is_winning_combo(combo) -> Tuple[bool, float]:
    """
    Проверка на выигрышную комбинацию

    :param combo: массив значений дайса (см. перем. casino)
    :return: пара ("есть_выигрыш?", "изменение счёта игрока")
    """

    # Все комбинации из трёх одинаковых оцениваем в 10 или 7 очков

    if combo[0] == combo[1] == combo[2]:
        if combo[0] == 'BAR':
            return True, 5.
        elif combo[0] == 'семь':
            return True, 3.
        elif combo[0] == 'лимон':
            return True, 2.
        elif combo[0] == 'виноград':
            return True, 2.
    else:
        return False, -1.


def get_casino_values(dice_value) -> List:
    """
    Возвращает то, что было на конкретном дайсе-казино
    :param dice_value: Число, которое вернул Bot API
    :return: строка, содержащая все выпавшие элементы

    Альтернативный вариант (ещё раз спасибо t.me/svinerus):
        return [casino[(dice_value - 1) // i % 4]for i in (1, 4, 16)]
    """
    dice_value -= 1
    result = []
    for _ in range(3):
        result.append(casino[dice_value % 4])
        dice_value //= 4
    return result
