import gspread
import datetime
import json
from help_module import add_day, convert_to_xlsDate
import time

sa = gspread.service_account("service_account.json")
wb = sa.open("Auto-table")


def new_worksheet(wb: gspread.Spreadsheet, sku_data: list):
    print(sku_data)
    example_sheet = wb.worksheet('Example')
    new_sku_sheet = wb.duplicate_sheet(example_sheet.id, new_sheet_name=sku_data[2])
    new_sku_sheet.update(range_name='A1:C1', values=[sku_data[:2]])
    return new_sku_sheet

def get_planned_values(manager_name, sku_sheet_name):
    sa = gspread.service_account("service_account.json")
    wb = sa.open(manager_name)
    sku_sheet = wb.worksheet(sku_sheet_name)

    if sku_sheet.acell("B8").value:
        planned_revenue = float(sku_sheet.acell("B8").value) / 30.5
    else:
        planned_revenue = 0

    if sku_sheet.acell("B9").value:
        planned_profit = float(sku_sheet.acell("B9").value) / 30.5
    else:
        planned_profit = 0

    if sku_sheet.acell("B10").value:
        planned_prom = float(sku_sheet.acell("B10").value) / 30.5
    else:
        planned_prom = 0

    if sku_sheet.acell("B10").value:
        planned_prom = float(sku_sheet.acell("B10").value) / 30.5
    else:
        planned_prom = 0

    if sku_sheet.acell("B11").value:
        cost = float(sku_sheet.acell("B11").value) / 30.5
    else:
        cost = 0

    res = {'planned_revenue': planned_revenue,
           'planned_profit': planned_profit,
           'planned_prom': planned_prom,
           'cost': cost}

    return res



def adding_data_daily(manager_name, sku_sheet_name, data, day):
    # Находим позицию столбца
    sa = gspread.service_account("service_account.json")
    wb = sa.open(manager_name)
    sku_sheet = wb.worksheet(sku_sheet_name)

    cell = sku_sheet.find(convert_to_xlsDate(day))
    date_col = cell.col
    with open('data_form.json', mode='r', encoding='utf-8') as json_form:
        data_form = json.load(json_form)
        count = 0
        for key in data_form.keys():
            count += 1
            if count > 55:
                time.sleep(60)
                count = 0
            if key in data:
                sku_sheet.update_cell(row=data_form[key], col=date_col, value=str(data[key]))
        sku_sheet.update_acell("C1", str(datetime.datetime.now()))

    # Прибыль
    # sku_sheet.update_cell(row=7, col=date_col, value="NO INF")


def add_new_worksheets(skus, manager):
    sa = gspread.service_account("service_account.json")
    wb = sa.open(manager)

    for sku in skus:
        new_worksheet(wb, sku)

    new_summary_table(wb, skus)


def new_summary_table(wb: gspread.Spreadsheet, skus):
    act_sheet = wb.worksheet('Общая')

    #WB table
    for i in range(0, len(skus)):
        val = int(act_sheet.acell('CI72').value) + 1
        act_sheet.update_cell(row=val, col=1, value=skus[i][1])
        act_sheet.update_cell(row=val, col=3, value=skus[i][0])
        act_sheet.update_acell('CI72', val)
    time.sleep(30)


def fill_summary_table(manager_name, sku, data, day):
    # Находим позицию столбца
    sa = gspread.service_account("service_account.json")
    wb = sa.open(manager_name)
    sku_sheet = wb.worksheet("Общая")

    cell = sku_sheet.find(convert_to_xlsDate(day))
    date_col = cell.col
    if 'Заказов на сумму, р' in data.keys():
        revenue_wb = data['Заказов на сумму, р']
    else:
        revenue_wb = '0'

    if sku_sheet.find(str(sku["skuWB"])):
        sku_row = sku_sheet.find(str(sku["skuWB"])).row
        sku_sheet.update_cell(row=sku_row, col=date_col, value=str(revenue_wb).replace('.',','))


# skus = [['176623617', '176623617', '176623617', 'Mix10'],
# ['169890350', '169890350', '169890350', 'Mix11'],
# ['152087679', '152087679', '152087679', 'Mix12'],
# ['204835978', '204835978', '204835978', 'Mix13'],
# ['16108355', '16108355', '16108355', 'Mix14']]
# sa = gspread.service_account("service_account.json")
# wb = sa.open("Менеджер2")

# skus = [['144299547', '144299547', '144299547', 'RE:START Keratin bomb shampoo and conditioner_WB SET'],
#         ['182765217', '182765217', '182765217', 'ДУБЛЬ RE:START Keratin bomb shampoo and conditioner_WB SET']]
# add_new_worksheets(skus)
#
# sa = gspread.service_account("service_account.json")
# wb = sa.open("Илария GOLD")
#
# add_new_worksheets(skus, "Илария GOLD")
