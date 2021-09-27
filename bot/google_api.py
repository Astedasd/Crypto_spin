import gspread
import os
from bot.db_service import prepare_channels_stat

#cred = os.path.join(DEFAULT_CONFIG_DIR, 'service_account.json')
#gc = gspread.service_account(filename='gspread/service_account.json')
# gc = gspread.service_account()
# sh = gc.open_by_key("1ucs0x5Q-c0qLwWILh9ynde74D_zB0cIxCllsDLRhnnU")

# print(sh.sheet1.get('A1'))


def upload_statistics(stats):
    gc = gspread.service_account()
    sh = gc.open_by_key("1ucs0x5Q-c0qLwWILh9ynde74D_zB0cIxCllsDLRhnnU")
    worksheet = sh.get_worksheet(1)
    new_row_number = len(worksheet.col_values(1)) + 1
    worksheet.update(f'A{new_row_number}:P{new_row_number}',
                     [[
                         stats['date'],
                         stats['balance'],
                         stats['deposits_sum'],
                         stats['deposits_number'],
                         stats['deposits_average'],
                         stats['withdraws_sum'],
                         stats['withdraws_number'],
                         stats['withdraws_average'],
                         stats['net_profit'],
                         stats['users'],
                         stats['registrations_number'],
                         stats['deletes_number'],
                         stats['new_users'],
                         stats['actions_number'],
                         stats['active_users']
                     ]])
    pass


def upload_channels_statistics(channels):
    gc = gspread.service_account()
    sh = gc.open_by_key("1ucs0x5Q-c0qLwWILh9ynde74D_zB0cIxCllsDLRhnnU")
    worksheet = sh.get_worksheet(2)
    # new_row_number = len(worksheet.col_values(1)) + 1
    i = 2
    for channel in channels:
        worksheet.update(f'A{i}:P{i}',
                         [[
                             channel['channel_name'],
                             channel['channel_code'],
                             channel['channel_visitors'],
                             channel['channel_registrations'],
                             channel['channel_promocode_num'],
                             channel['channel_promocode_sum'],
                             channel['channel_deposits_num'],
                             channel['channel_deposits_sum'],
                             channel['channel_withdraws_num'],
                             channel['channel_withdraws_sum']
                         ]])
        i += 1
    pass


upload_channels_statistics(prepare_channels_stat())