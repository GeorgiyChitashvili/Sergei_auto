import telebot
import telebot.types as types
import json
# from ggl import new_workbook
from help_module import process_message
from config import BOT_API
from ggl_sheets import add_new_worksheets


bot = telebot.TeleBot(BOT_API)
JSON_BD = 'managers.json'

@bot.message_handler(commands=['start'])
def main(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True,
                                         one_time_keyboard=True)
    btn1 = types.KeyboardButton(text="Добавить SKU")
    btn2 = types.KeyboardButton(text="Удалить SKU")
    keyboard.row(btn1, btn2)

    bot.send_message(message.chat.id, "Выберите действие", reply_markup=keyboard)
    bot.register_next_step_handler(callback=callback_check, message=message)


def callback_check(message: types.Message):
    if message.text == "Добавить SKU":
        bot.send_message(message.chat.id,
                         "Выбрано: Добавить SKU. "
                         "В одном сообщении на разных строках введите данные в следующем формате:\n"
                         "Артикул внутренний - Артикул ВБ - Опознавательное имя артикула\n"
                         "Сохраняйте знаки-разделители '-' и пробелы между ними."
                         "В случае некорректности данных программа не "
                         "будет работать правильно. Удостоверьтесь, что артикулы верны")
        bot.register_next_step_handler(callback=add_sku, message=message)

    elif message.text == "Удалить SKU":
        bot.send_message(message.chat.id,
                         "Выбрано: Удалить SKU. "
                         "В одном сообщении на разных строках введите данные в следующем формате:\n"
                         "Артикул ВБ\n"
                         "В случае некорректности данных программа не "
                         "будет работать правильно. Удостоверьтесь, что артикулы верны")
        bot.register_next_step_handler(callback=delete_sku, message=message)

    else:
        bot.send_message(message.chat.id, 'Простите, я вас не понимаю!')
        bot.register_next_step_handler(callback=main, message=message)
        return ''


def add_sku(message: types.Message):
    # Adding SKU's to JSON-format DB
    # Обработка переданных данных
    try:
        manager, sku_data = process_message(message, JSON_BD, 0)
        print(sku_data)
        add_new_worksheets(sku_data, manager)

        bot.send_message(message.chat.id, text='Артикулы добавлены')
    except BaseException as e:
        bot.send_message(message.chat.id, text='Какая-то ошибка')


def delete_sku(message: types.Message):
    try:
        # Deleting SKU's from JSON-format DB
        sku_data = process_message(message, JSON_BD, 2)

        bot.send_message(message.chat.id, text='Артикулы удалены')
    except BaseException as e:
        bot.send_message(message.chat.id, text='Какая-то ошибка')


if __name__ == "__main__":
    bot.polling(none_stop=True)

