import pandas as pd
import requests
import datetime as dt
import json
import time
from help_module import check_response, correct_division
from ggl_sheets import adding_data_daily, fill_summary_table, get_planned_values
from config import WB_API
import schedule


def get_data(sku_input, date, API_WB):
    resulting_dict = {}
    # try:
    try:
        sku = sku_input["skuWB"]

        url_incomes = 'https://statistics-api.wildberries.ru/api/v1/supplier/sales'
        headers = {'Authorization': API_WB}
        param_request = {'dateFrom': date, "flag": "1"}
        response_incomes = requests.get(url_incomes, headers=headers, params=param_request).json()

        df = pd.DataFrame(response_incomes)
        df.set_index('srid')
        sku_df = df[df["nmId"] == int(sku)]


        # Выручка магазина по артикулу, р
        day_sum = sku_df["priceWithDisc"].sum()
        resulting_dict["Выкупов на сумму, р"] = int(day_sum)

        # Продажи за день по артикулу, шт
        count_sum = sku_df["srid"].count()
        resulting_dict["Выкупы, шт"] = int(count_sum)

        # Заказы
        url_incomes = 'https://statistics-api.wildberries.ru/api/v1/supplier/orders'
        headers = {'Authorization': API_WB}
        param_request = {'dateFrom': date, "flag": "1"}
        response_incomes = requests.get(url_incomes, headers=headers, params=param_request).json()

        df = pd.DataFrame(response_incomes)
        df.set_index('srid')
        sku_df = df[df["nmId"] == sku]

        # Заказов за день по артикулу, шт
        count_sum = sku_df["priceWithDisc"].count()
        if count_sum:
            resulting_dict["Заказы, шт"] = int(count_sum)

        # Заказов магазина по артикулу, р
        day_sum = sku_df["priceWithDisc"].sum()
        resulting_dict["Заказов на сумму, р"] = int(float(day_sum))

        # СПП
        spp = sku_df['spp'].max()
        resulting_dict["СПП"] = str(spp) + "%"

        # Цена Mixit
        price_mixit = sku_df["priceWithDisc"].min()
        if price_mixit > 0:
            resulting_dict["Цена до СПП"] = int(price_mixit)

        # Цена Mixit СПП
        price_mixit_spp = sku_df["finishedPrice"].min()
        resulting_dict["Цена после СПП"] = int(price_mixit_spp)
    except BaseException as e:
        print(f"FAILED WB REVENUE WITH {e}")

    # Округи
    okrugi_data = []
    try:
        for country in countries:
            if "nmId" in sku_df.columns:
                info = sku_df[sku_df["countryName"] == country]
                okrugi_data.append((country, len(info)))
            else:
                print(okrugi_data)
        for okrug in okrugi:
            if "nmId" in sku_df.columns:
                info = sku_df[sku_df["oblastOkrugName"] == okrug]
                okrugi_data.append((okrug, len(info)))
                print(info)
                print(okrugi_data)
            else:
                okrugi_data.append((okrug, 0))
        for okrug in okrugi_data:
            resulting_dict[okrug[0]] = okrug[1]
    except BaseException as e:
        print(f"FAILED WB OKRUGI WITH {e}")

    # Склады
    if date == str(dt.date.today()):
        url_incomes = 'https://statistics-api.wildberries.ru/api/v1/supplier/stocks'
        headers = {'Authorization': API_WB}
        param_request = {'dateFrom': date}
        response_incomes = requests.get(url_incomes, headers=headers, params=param_request)

        df = pd.DataFrame(response_incomes.json())

        if "nmId" in df.columns:
            filter_df = df[(df["nmId"] == sku)]
            filter_df.set_index('nmId')
        warehouse_data = []

        for wh in warehouse:
            if "nmId" in filter_df.columns:
                info = filter_df[filter_df['warehouseName'] == wh]['quantity'].sum()
                warehouse_data.append((wh, int(info)))
            else:
                warehouse_data.append((wh, 0))

        resulting_dict['Всего остатков'] = int(filter_df['quantity'].sum())
        for wh in warehouse_data:
            resulting_dict[wh[0]] = wh[1]

    # Воронка
    url_analytics = 'https://seller-analytics-api.wildberries.ru/api/v2/nm-report/detail/history'
    headers = {'Authorization': API_WB, "Content-Type": "application/json"}
    body_post = {'nmIDs': [sku],
                 'period': {"begin": date,
                            "end": date},
                 'aggregationLevel': "day"}
    response_incomes = requests.post(url_analytics, headers=headers, data=json.dumps(body_post))

    data = response_incomes.json()
    if data['data']:
        dataset = data['data'][0]["history"][0]

        # Перешли
        resulting_dict['Перешли в карточку'] = int(dataset['openCardCount'])

        # Корзина
        resulting_dict['Добавили в корзину'] = int(dataset['addToCartCount'])

        # % из карточки в корзину
        resulting_dict['Конверсия в корзину'] = str(dataset['addToCartConversion']) + "%"

        # Заказы
        resulting_dict['Заказано'] = int(dataset['ordersCount'])

        # Из корзины в заказ
        resulting_dict['Конверсия в заказ'] = str(dataset['cartToOrderConversion']) + "%"

        # CR
        resulting_dict['CR'] = str(dataset['addToCartConversion'] * dataset['cartToOrderConversion'] / 100) + "%"

    ark_ids = []
    search_ids = []
    # Реклама
    # Получить списки компаний
    try:
        url_analytics = 'https://advert-api.wb.ru/adv/v1/promotion/count'
        headers = {'Authorization': API_WB, "Content-Type": "application/json"}
        response_incomes = requests.get(url_analytics, headers=headers)
        data = response_incomes.json()

        ids = []
        for advert in data["adverts"]:
            if advert["status"] in (9, 11) and advert["type"] in (8, 9):
                for element in advert["advert_list"]:
                    ids.append(element["advertId"])
                    time.sleep(1)

        # Сбор информации о кампаниях по Артикулу

        while ids:
            tmp_ids = []
            while len(tmp_ids) < 50 and ids:
                tmp_ids.append(ids[-1])
                ids.remove(ids[-1])

            url_analytics = 'https://advert-api.wb.ru/adv/v1/promotion/adverts'
            headers = {'Authorization': API_WB, "Content-Type": "application/json"}
            response_incomes = requests.post(url_analytics, headers=headers, data=json.dumps(tmp_ids))
            data = response_incomes.json()

            for element in data:
                if element['type'] == 9 and element['unitedParams'][0]['nms'][0] == sku:
                    search_ids.append(element['advertId'])
                elif element['type'] == 8 and element['autoParams']['nms'][0] == sku:
                    ark_ids.append(element['advertId'])

            time.sleep(1)
    except BaseException:
        print("Error in promotion/count")

    # Сбор информации по конкретным кампаниям
    time.sleep(10)
    url_analytics = 'https://advert-api.wb.ru/adv/v2/fullstats'
    request_body = [{"id": id, "dates": [date]} for id in search_ids + ark_ids]
    print(request_body)
    try:
        response_incomes = requests.post(url_analytics, headers=headers, data=json.dumps(request_body))
        data = response_incomes.json()
    except BaseException:
        print(f"error on {url_analytics}")

    print(data)

    search_stats = {'views': 0, 'clicks': 0, 'buckets': 0, 'orders': 0, 'sum': 0, 'orders_sum': 0}
    ark_stats = {'views': 0, 'clicks': 0, 'buckets': 0, 'orders': 0, 'sum': 0, 'orders_sum': 0}
    overall_stats = {'views': 0, 'clicks': 0, 'buckets': 0, 'orders': 0, 'sum': 0, 'orders_sum': 0}
    if data and 'error' not in data and 'code' not in data:
        for advert in data:
            if advert["advertId"] in ark_ids:
                ark_stats['views'] += advert["views"]
                ark_stats['clicks'] += advert["clicks"]
                ark_stats['buckets'] += advert["atbs"]
                ark_stats['orders'] += advert["orders"]
                ark_stats['sum'] += advert["sum"]
                ark_stats['orders_sum'] += advert['sum_price']
            elif advert["advertId"] in search_ids:
                search_stats['views'] += advert["views"]
                search_stats['clicks'] += advert["clicks"]
                search_stats['buckets'] += advert["atbs"]
                search_stats['orders'] += advert["orders"]
                search_stats['sum'] += advert["sum"]
                search_stats['orders_sum'] += advert['sum_price']

        try:
            overall_stats['views'] = ark_stats['views'] + search_stats['views']
            overall_stats['clicks'] = ark_stats['views'] + search_stats['views']
            overall_stats['buckets'] = ark_stats['views'] + search_stats['views']
            overall_stats['orders'] = ark_stats['views'] + search_stats['views']
            overall_stats['sum'] = ark_stats['views'] + search_stats['views']
            overall_stats['orders_sum'] = ark_stats['views'] + search_stats['views']
        except BaseException as e:
            print(f'Error {e}')


    resulting_dict['Показы (реклама)'] = int(overall_stats['views'])
    resulting_dict['Перешли в карточку (реклама)'] = int(overall_stats['clicks'])
    resulting_dict['Добавили в корзину (реклама)'] = int(overall_stats['buckets'])
    resulting_dict['Конверсия в корзину (реклама)'] = str(
        correct_division(overall_stats['buckets'], overall_stats['clicks']) * 100) + "%"
    resulting_dict['Заказано (реклама)'] = int(overall_stats['orders'])
    resulting_dict['Конверсия в заказ (реклама)'] = str(
        correct_division(overall_stats['orders'], overall_stats['buckets']) * 100) + "%"
    resulting_dict['CR (реклама)'] = str(correct_division(overall_stats['buckets'], overall_stats['clicks']) * 100
                                   * correct_division(overall_stats['orders'], overall_stats['buckets'])) + "%"
    resulting_dict['CPC'] = correct_division(overall_stats['sum'], overall_stats['clicks'])
    resulting_dict['CTR'] = str(correct_division(overall_stats['clicks'], overall_stats['views']) * 100) + "%"
    resulting_dict['Бюджет Факт'] = int(overall_stats['sum'])
    resulting_dict['Стоимость корзины'] = correct_division(overall_stats['sum'], overall_stats['buckets'])
    resulting_dict['Стоимость заказа'] = correct_division(overall_stats['sum'], overall_stats['orders'])


    resulting_dict['Просмотры АРК'] = int(ark_stats['views'])
    resulting_dict['Клики АРК'] = int(ark_stats['clicks'])
    resulting_dict['CTR АРК'] = str(correct_division(ark_stats['clicks'], ark_stats['views']) * 100) + "%"
    resulting_dict['Корзины АРК'] = int(ark_stats['buckets'])
    resulting_dict['Конверсия в корзину АРК'] = str(
        correct_division(ark_stats['buckets'], ark_stats['clicks']) * 100) + "%"
    resulting_dict['Заказы АРК'] = int(ark_stats['orders'])
    resulting_dict['Конверсия в заказ АРК'] = str(
        correct_division(ark_stats['orders'], ark_stats['buckets']) * 100) + "%"
    resulting_dict['CR АРК'] = str(correct_division(ark_stats['buckets'], ark_stats['clicks']) * 100
                                   * correct_division(ark_stats['orders'], ark_stats['buckets'])) + "%"
    resulting_dict['Затраты АРК'] = int(ark_stats['sum'])
    resulting_dict['CPC АРК'] = correct_division(resulting_dict['Затраты АРК'], resulting_dict['Клики АРК'])
    resulting_dict['CPO АРК'] = correct_division(resulting_dict['Затраты АРК'], resulting_dict['Заказы АРК'])
    resulting_dict['Ставка АРК'] = int(correct_division(ark_stats['sum'], ark_stats['views']) * 1000)

    resulting_dict['Просмотры ПК'] = int(search_stats['views'])
    resulting_dict['Клики ПК'] = int(search_stats['clicks'])
    resulting_dict['CTR ПК'] = str(correct_division(search_stats['clicks'], search_stats['views']) * 100) + "%"
    resulting_dict['Корзины ПК'] = int(search_stats['buckets'])
    resulting_dict['Конверсия в корзину ПК'] = str(
        correct_division(search_stats['buckets'], search_stats['clicks']) * 100) + "%"
    resulting_dict['Заказы ПК'] = int(search_stats['orders'])
    resulting_dict['Конверсия в заказ ПК'] = str(
        correct_division(search_stats['orders'], search_stats['buckets']) * 100) + "%"
    resulting_dict['CR ПК'] = str(correct_division(search_stats['buckets'], search_stats['clicks']) * 100
                                  * correct_division(search_stats['orders'], search_stats['buckets'])) + "%"
    resulting_dict['Затраты ПК'] = int(search_stats['sum'])
    resulting_dict['CPC ПК'] = correct_division(resulting_dict['Затраты ПК'], resulting_dict['Клики ПК'])
    resulting_dict['CPO ПК'] = correct_division(resulting_dict['Затраты ПК'], resulting_dict['Заказы ПК'])
    resulting_dict['Ставка ПК'] = int(correct_division(search_stats['sum'], search_stats['views']) * 1000)

    resulting_dict['Сумма заказов ПК'] = search_stats['orders_sum']
    resulting_dict['Сумма заказов АРК'] = ark_stats['orders_sum']
    # except BaseException:
    #     print(f"Error in WB {sku_input} {date}")

    #first
    sku = sku_input["skuName"]
    manager = "Auto-table"

    values = get_planned_values(manager, sku)
    if values['planned_revenue'] is None:
        resulting_dict["Заказы ПЛАН, р"] = 0
    else:
        resulting_dict["Заказы ПЛАН, р"] = values['planned_revenue']
    if values['planned_profit'] is None:
        resulting_dict['Бюджет План'] = 0
    else:
        resulting_dict['Бюджет План'] = values['planned_profit']

    if values['planned_prom'] is None:
        resulting_dict["Планируемая Чистая Прибыль"] = 0
    else:
        resulting_dict["Планируемая Чистая Прибыль"] = values['planned_prom']

    # Выгрузка данных
    processed_dict = {}

    for key in resulting_dict:
        if '.' in str(resulting_dict[key]):
            processed_dict[key] = str(resulting_dict[key]).replace('.', ',')
        else:
            processed_dict[key] = str(resulting_dict[key])

    return processed_dict


warehouse = ['Электросталь', 'Коледино', 'Казань', 'Краснодар', 'Новосемейкино', 'Тула', 'Невинномысск',
             'Подольск', 'Санкт-Петербург (Уткина Заводь)', 'Екатеринбург - Перспективный 12']

countries = ['Россия', 'Казахстан', 'Армения', 'Беларусь']

okrugi = ["Приволжский федеральный округ", "Сибирский федеральный округ", "Центральный федеральный округ",
          "Дальневосточный федеральный округ", "Cеверо-Западный федеральный округ", "Уральский федеральный округ",
          "Южный федеральный округ", "Северо-Кавказский федеральный округ"]


def main(date):
    with open('managers.json', mode='r', encoding='utf-8') as json_bd:
        managers_data = json.load(json_bd)
        for manager in managers_data:
            for sku in managers_data[manager]:
                print(f"Running {sku} {date} for {dt.datetime.now()} of {manager}")

                RETRY_COUNT = 0
                while RETRY_COUNT < 2:
                    try:
                        data = get_data(managers_data[manager][sku], str(date), WB_API)
                        adding_data_daily(manager, managers_data[manager][sku]["skuName"], data, str(date))
                        fill_summary_table(manager, managers_data[manager][sku], data, str(date))
                        print(f"DONE on {manager} {sku} {date}")
                        time.sleep(150)
                        break
                    except BaseException:
                        print(f"ERROR on {manager} {sku} {date} trying {RETRY_COUNT} time")
                        RETRY_COUNT += 1
                        time.sleep(150)

            # iter_date = dt.date(2024, 2, 1)
            # end_date = dt.date(2024, 3, 29)
            # RETRY_COUNT = 0
            # while (iter_date < end_date):
            #     try:
            #         data = get_data(int(sku), str(iter_date))
            #         adding_data_daily(manager, managers_data[manager][sku]["skuName"], data, str(iter_date))
            #         iter_date += dt.timedelta(days=1)
            #         time.sleep(71)
            #         RETRY_COUNT = 0
            #     except BaseException:
            #         print(f"error on {manager} {sku} {iter_date}")
            #         if RETRY_COUNT < 2:
            #             RETRY_COUNT += 1
            #             time.sleep(120)
            #         else:
            #             iter_date += dt.timedelta(days=1)
            #             RETRY_COUNT = 0
            #             time.sleep(120)


# schedule.every().day.at("00:01", "Europe/Moscow").do(main())

if __name__ == "__main__":
    while True:
        date = dt.date.today()
        main(date)
        time.sleep(180)
        main(date - dt.timedelta(1))
        time.sleep(180)
        main(date)
        time.sleep(180)
        main(date - dt.timedelta(2))
        time.sleep(180)
        main(date)
        time.sleep(180)
        main(date)
        time.sleep(180)


    # dates = [dt.date.today() - dt.timedelta(i) for i in range(5, -1, -1)]
    # for date in dates:
    #     main(date)

# asdads
