#!/usr/bin/python3

import utils
import logging
from datetime import datetime
from fuzzywuzzy import process, fuzz
import random

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

import sqlite3
from sqlite3 import Error


def command(bot, update):
    raw_text = update.message.text.strip()
    command = raw_text.split(" ")[0]

    result = process.extractOne(command, list(available_commands.keys()), scorer=fuzz.ratio)
    print(result)
    if result[1] < 50:
        out = "Oops, I'm not sure which command you mean. Possible options are:\n" + instructions()
        bot.send_message(update.message.from_user.id,
                         text=out,
                         parse_mode=telegram.ParseMode.HTML)
    else:
        available_commands[result[0]][0](bot, update)


def instructions():
    out = ""
    for command_name, (function, command_description) in available_commands.items():
        out += "/{} - <i>{}</i>\n".format(command_name, command_description)
    return out


def zapfen(bot, update):
    raw_text = update.message.text.strip()
    command = raw_text.split(" ")[0]
    text = raw_text.replace(command, "").strip()
    choices = [["Bier"], ["Shot"], ["Drink"], ["Wein"]]
    show_keyboard(bot, update, choices, "zapfen", "Was geds?")


def delete(bot, update):
    command = "SELECT ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and deleted = 0 ORDER BY consumptions.ts ASC LIMIT 5;".format(update.message.from_user.id)
    drinks = list(execute_command(db_file, command))

    if len(drinks) > 0:
        choices = []
        for timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            choices.append([text])
        show_keyboard(bot, update, choices, "delete", "Wele esch z'vell?")
    else:
        bot.send_message(update.message.from_user.id,
                         text="Du hesch jo gar nüt tronke!",
                         parse_mode=telegram.ParseMode.HTML)


def undelete(bot, update):
    command = "SELECT ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and deleted = 1 ORDER BY consumptions.ts ASC LIMIT 5;".format(update.message.from_user.id)
    drinks = list(execute_command(db_file, command))

    if len(drinks) > 0:
        choices = []
        for timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            choices.append([text])
        show_keyboard(bot, update, choices, "undelete", "Wele esch doch ned z'vell gsi?")
    else:
        bot.send_message(update.message.from_user.id,
                         text="Du hesch no gar nüüt glöscht!",
                         parse_mode=telegram.ParseMode.HTML)


def show_keyboard(bot, update, choices, action, message, command=None, user_id=None):
    keyboard = []
    if user_id is None:
        user_id = update.message.from_user.id
    if command is None:
        command = update.message.text.strip().split(" ")[0]
    for row in choices:
        keyboard.append([])
        for column in row:
            callback_data = "{} {} {} {}".format(action, user_id, command, column)
            keyboard[-1].append(
                InlineKeyboardButton(column, callback_data=callback_data))
    bot.send_message(user_id, message, reply_markup=InlineKeyboardMarkup(keyboard))


def keyboard_response(bot, update):
    query = update.callback_query
    data = query.data.split(" ")
    action = data[0]
    user_id = data[1]
    command = data[2]
    value = " ".join(data[3:])

    bot.deleteMessage(chat_id=query.message.chat_id,
                      message_id=query.message.message_id)

    if action == "zapfen":
        if value == "Bier":
            choices = [["3dl"], ["5dl"], ["1l"]]
            show_keyboard(bot, update, choices, "bier", "Wie gross?", command=command, user_id=user_id)
        elif value == "Drink":
            choices = [["3dl"], ["5dl"], ["1l"]]
            show_keyboard(bot, update, choices, "drink", "Wie gross?", command=command, user_id=user_id)
        elif value == "Shot":
            choices = [["1cl"], ["2cl"], ["4cl"]]
            show_keyboard(bot, update, choices, "shot", "Wie gross?", command=command, user_id=user_id)
        elif value == "Wein":
            choices = [["1dl"], ["2dl"]]
            show_keyboard(bot, update, choices, "wein", "Wie gross?", command=command, user_id=user_id)
    elif action == "highscore":
        second = 1000
        minute = 60 * second
        hour = 60 * minute
        day = 24 * hour
        week = 7 * day
        if value.endswith("w"):
            time = float(value.replace("w", "")) * week
        elif value.endswith("d"):
            time = float(value.replace("d", "")) * day
        elif value.endswith("h"):
            time = float(value.replace("h", "")) * hour
        elif value.endswith("m"):
            time = float(value.replace("m", "")) * minute
        else:
            time = 1000
        best = get_best(time)
        if len(best) == 0:
            out = "<i>Noone has participated in this timeframe</i>\n".format(value)
        else:
            out = "<b>Highscore for the last {}:</b>\n".format(value)
            for rank, (amount, name) in enumerate(best):
                amount_in_beer = amount / 5
                out += "<b>{} {}</b>: {:.1f}l Bier\n".format(rank + 1, name, amount_in_beer)
        bot.send_message(user_id, out, parse_mode=telegram.ParseMode.HTML)
    elif action == "delete":
        command = "SELECT consumptions.id,ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and deleted = 0 ORDER BY consumptions.ts ASC LIMIT 5;".format(user_id)
        drinks = list(execute_command(db_file, command))
        for consumption_id, timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            if text == value:
                command = "UPDATE consumptions SET deleted = 1 WHERE id = {}".format(consumption_id)
                execute_command(db_file, command)
                bot.send_message(user_id, "Ok, han {}l {} glöscht.".format(amount, drink), parse_mode=telegram.ParseMode.HTML)
    elif action == "undelete":
        command = "SELECT consumptions.id,ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and deleted = 1 ORDER BY consumptions.ts ASC LIMIT 5;".format(user_id)
        drinks = list(execute_command(db_file, command))
        for consumption_id, timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            if text == value:
                command = "UPDATE consumptions SET deleted = 0 WHERE id = {}".format(consumption_id)
                execute_command(db_file, command)
                bot.send_message(user_id, "Ok, hand {}l {} weder zroggholt.".format(amount, drink), parse_mode=telegram.ParseMode.HTML)
    else:
        add_drink(bot, user_id, command, action, value)


def add_drink(bot, user_id, user_command, drink, size_str):
    drink_id = drink_ids[drink]

    if size_str.endswith("cl"):
        size = float(size_str.replace("cl", "")) / 100
    elif size_str.endswith("dl"):
        size = float(size_str.replace("dl", "")) / 10
    elif size_str.endswith("l"):
        size = float(size_str.replace("l", ""))

    timestamp = datetime.timestamp(datetime.now())

    precision = fuzz.ratio(user_command.lower(), "/zapfen")

    with open("trinksprüche.txt") as f:
        sprueche = f.read().split("\n\n")
    spruch = random.choice(sprueche)
    out = "Du trenksch {} {}.\n\n<i>{}</i>".format(size_str, drink, spruch)
    bot.send_message(user_id, out, parse_mode=telegram.ParseMode.HTML)

    command = "INSERT INTO consumptions (user_id, drink_id, amount, ts, command, precision, deleted) VALUES ({}, {}, {}, {}, '{}', {}, 0);".format(user_id, drink_id, size, timestamp, user_command, precision)
    execute_command(db_file, command)


def highscore(bot, update):
    choices = [["1h"], ["3h"], ["1d"], ["1w"]]
    show_keyboard(bot, update, choices, "highscore", "Wie lang?")


def get_best(time_ms):
    min_timestamp = datetime.timestamp(datetime.now()) - time_ms
    command = "SELECT SUM(consumptions.amount*drinks.vol),users.name FROM consumptions JOIN users ON consumptions.user_id = users.id JOIN drinks on consumptions.drink_id = drinks.id WHERE consumptions.ts > {} and deleted = 0 GROUP BY consumptions.user_id ORDER BY SUM(consumptions.amount*drinks.vol) DESC;".format(min_timestamp)
    return list(execute_command(db_file, command))


def execute_command(db_file, command):
    """ create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        logger.info("executing " + command)
        cur.execute(command)
        conn.commit()
        out = cur.fetchall()
        logger.info(out)
        return out
    except Error as e:
        print(e)
    finally:
        conn.close()
    return None


def start(bot, update):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    command = "INSERT INTO users (id,name) VALUES ({}, '{}');".format(user_id, user_name)
    execute_command(db_file, command)
    bot.send_message(update.message.from_user.id,
                     text="Welcome to Zapfen Bot. These are the commands I know:\n" + instructions(),
                     parse_mode=telegram.ParseMode.HTML)


db_file = "zapfen.db"
drink_ids = {"bier": 0, "drink": 1, "shot": 2, "wein": 3}
available_commands = {"zapfen": (zapfen, "Add drink"),
                      "highscore": (highscore, "Show highscore"),
                      "delete": (delete, "Delete drink"),
                      "undelete": (undelete, "undelete drink")}

if __name__ == "__main__":
    updater = Updater(token=utils.apikey)
    dispatcher = updater.dispatcher
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger()
    # specified commands
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.all, command))
    updater.dispatcher.add_handler(CallbackQueryHandler(keyboard_response))

    updater.start_polling()
