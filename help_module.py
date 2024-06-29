import requests
import json
import telebot.types as types
import datetime as dt


def check_response(response: requests.Response):
    return True


def process_message(message: types.Message, json_file: str, flag=int):
    data = message.text
    manager = "Auto-table"
    sku_data = [i.split(' - ') for i in data.split('\n')]

    # Передача обработанных данных в JSON-БД
    with open(json_file, mode='r', encoding='utf-8') as JSON_DB:
        data = json.load(JSON_DB)
        if flag == 1:
            data[manager] = {}
        for sku in sku_data:
            if flag in (0, 1):
                data[manager][sku[0]] = {"sku": sku[0],
                                         "skuWB": int(sku[1]),
                                         "skuName": sku[2]}
            elif flag == 2:
                if sku in data[manager]:
                    del data[manager][sku]
    with open(json_file, mode='w', encoding='utf-8') as JSON_DB:
        json.dump(data, JSON_DB)

    sku_processed_data = [[i[0], int(i[1]), i[2]] for i in sku_data]

    return manager, sku_processed_data


def add_day(date):
    date = dt.datetime.strftime((dt.datetime.strptime(date, "%Y-%m-%d") + dt.timedelta(days=1)), "%Y-%m-%d")
    return date


def convert_to_xlsDate(date):
    base = dt.datetime.strftime((dt.datetime.strptime(date, "%Y-%m-%d")), "%d.%m.%Y")
    return base


def correct_division(d1, d2):
    if d2 == 0:
        return 0
    else:
        return round(d1/d2, 2)