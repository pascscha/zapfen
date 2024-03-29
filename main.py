#!/usr/bin/python3

import utils
import logging
from datetime import datetime
from fuzzywuzzy import process, fuzz
import random
import operator

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
    choices = [["Bier"], ["Shot"], ["Cocktail"], ["Wein"]]
    show_keyboard(bot, update, choices, "zapfen", "Was geds?")


def delete(bot, update):
    command = "SELECT ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and consumptions.deleted = 0 ORDER BY consumptions.ts DESC LIMIT 5;".format(update.message.from_user.id)
    drinks = list(execute_command(db_file, command))

    if len(drinks) > 0:
        choices = []
        for timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            choices.append([text])
        choices.reverse()
        show_keyboard(bot, update, choices, "delete", "Wele esch z'vell?")
    else:
        bot.send_message(update.message.from_user.id,
                         text="Du hesch jo no gar nüt zapft!",
                         parse_mode=telegram.ParseMode.HTML)


def undelete(bot, update):
    command = "SELECT ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and consumptions.deleted = 1 ORDER BY consumptions.ts DESC LIMIT 5;".format(update.message.from_user.id)
    drinks = list(execute_command(db_file, command))

    if len(drinks) > 0:
        choices = []
        for timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            choices.append([text])
        choices.reverse()
        show_keyboard(bot, update, choices, "undelete", "Wele esch doch ned z'vell gsi?")
    else:
        bot.send_message(update.message.from_user.id,
                         text="Du hesch no gar nüüt glöscht!",
                         parse_mode=telegram.ParseMode.HTML)


def get_gender(bot, update):
    choices = [["Bueb", "Meidschi"], ["Wish not to disclose"]]
    show_keyboard(bot, update, choices, "gender", "Was besch du?")


def get_weight(bot, update):
    raw_text = update.message.text.strip()
    command = raw_text.split(" ")[0]
    try:
        weight = raw_text.split(" ")[1]
        if "kg" in weight:
            weight = weight.replace("kg", "")
            weight = float(weight)
        elif "g" in weight:
            weight = weight.replace("g", "")
            weight = float(weight) * 1000
        else:
            weight = float(weight)
    except Exception as e:
        print(e)
        bot.send_message(update.message.from_user.id,
                         text="Das hani ned verstande. Korrekts biispel: <code>/weight 75kg</code>",
                         parse_mode=telegram.ParseMode.HTML)
        return

    command = "UPDATE users SET weight = {} WHERE id = {}".format(weight, update.message.from_user.id)
    execute_command(db_file, command)
    bot.send_message(update.message.from_user.id,
                     text="Du besch jetzt {:.0f}kg schwär!".format(weight),
                     parse_mode=telegram.ParseMode.HTML)


def get_height(bot, update):
    raw_text = update.message.text.strip()
    command = raw_text.split(" ")[0]
    try:
        height = raw_text.split(" ")[1]
        if "m" in height:
            height = height.replace("m", "")
            height = float(height)
        elif "cm" in height:
            height = height.replace("cm", "")
            height = float(height) * 100
        else:
            height = float(height)
            if height < 10:
                height *= 100

    except:
        bot.send_message(update.message.from_user.id,
                         text="Das hani ned verstande. Korrekts biispel: <code>/height 183</code>",
                         parse_mode=telegram.ParseMode.HTML)
        return

    command = "UPDATE users SET height = {} WHERE id = {}".format(height, update.message.from_user.id)
    execute_command(db_file, command)
    bot.send_message(update.message.from_user.id,
                     text="Du besch jetzt {:.0f}cm gross!".format(height),
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
            choices = [["1dl"], ["3dl"], ["5dl"], ["1l"]]
            show_keyboard(bot, update, choices, "bier", "Wie gross?", command=command, user_id=user_id)
        elif value == "Cocktail":
            choices = [["2dl"], ["3dl"], ["5l"]]
            show_keyboard(bot, update, choices, "cocktail", "Wie gross?", command=command, user_id=user_id)
        elif value == "Shot":
            choices = [["1cl"], ["2cl"], ["4cl"]]
            show_keyboard(bot, update, choices, "shot", "Wie gross?", command=command, user_id=user_id)
        elif value == "Wein":
            choices = [["1dl"], ["2dl"]]
            show_keyboard(bot, update, choices, "wein", "Wie gross?", command=command, user_id=user_id)
    elif action == "highscore":
        second = 1
        minute = 60 * second
        hour = 60 * minute
        day = 24 * hour
        week = 7 * day
        now = datetime.now()
        now_ts = datetime.timestamp(now)
        if value == "∞":
            time = 0
            out = "<b>Eternal Ranking</b>\n"
        elif value == "Promille":
            time = 0
            out = "<b>Promille Ranking</b>\n"
        elif value == "1h":
            time = now_ts - hour
            out = "<b>Highscore for the last hour:</b>\n"
        elif value == "1w":
            time = now_ts - week
            out = "<b>Highscore for the last week:</b>\n"
        elif value == "10:00":
            if now.hour >= 10:
                out = "<b>Highscore since 10:00 today:</b>\n"
                hours = now.hour - 10
            else:
                out = "<b>Highscore since 10:00 yesterday:</b>\n"
                hours = now.hour + 14
            time = now_ts - (hours * hour + now.minute * minute + now.second * second)
        else:
            out = "<b>There was an internal error so here's the ranking for the last minute:</b>\n"
            time = minute
        best = get_best(time)
        if len(best) == 0:
            out = "<i>Noone has participated in this timeframe</i>\n"
        else:
            highscore_list = []
            for amount, name, highscore_user_id in best:
                amount_in_beer = amount / 5
                promille, relevant_amount = promille_rechner(highscore_user_id)
                highscore_list.append((name, amount_in_beer, promille, relevant_amount))

            if value == "Promille":
                highscore_list.sort(key=operator.itemgetter(2), reverse=True)
                count = 0
                for rank, (name, amount_in_beer, promille, relevant_amount) in enumerate(highscore_list):
                    if relevant_amount == 0:
                        break
                    if relevant_amount is not None:
                        if promille is not None:
                            promille = " ({:.2f}‰)".format(promille)
                        else:
                            promille = ""
                        out += "<b>{} {}</b>: {:.1f}l Bier{}\n".format(rank + 1, name, relevant_amount / 5, promille)
                        count += 1
                if count == 0:
                    out = "<i>Everyone is sober.</i>\n"
            else:
                for rank, (name, amount_in_beer, promille, relevant_amount) in enumerate(highscore_list):
                    if promille is not None:
                        promille = " ({:.2f}‰)".format(promille)
                    else:
                        promille = ""
                    out += "<b>{} {}</b>: {:.1f}l Bier{}\n".format(rank + 1, name, amount_in_beer, promille)
        bot.send_message(user_id, out, parse_mode=telegram.ParseMode.HTML)

    elif action == "delete":
        command = "SELECT consumptions.id,ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and deleted = 0 ORDER BY consumptions.ts DESC LIMIT 5;".format(user_id)
        drinks = list(execute_command(db_file, command))
        for consumption_id, timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            if text == value:
                command = "UPDATE consumptions SET deleted = 1 WHERE id = {}".format(consumption_id)
                execute_command(db_file, command)
                bot.send_message(user_id, "Ok, han {}l {} glöscht.".format(amount, drink), parse_mode=telegram.ParseMode.HTML)
    elif action == "undelete":
        command = "SELECT consumptions.id,ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and deleted = 1 ORDER BY consumptions.ts DESC LIMIT 5;".format(user_id)
        drinks = list(execute_command(db_file, command))
        for consumption_id, timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            if text == value:
                command = "UPDATE consumptions SET deleted = 0 WHERE id = {}".format(consumption_id)
                execute_command(db_file, command)
                bot.send_message(user_id, "Ok, hand {}l {} weder zroggholt.".format(amount, drink), parse_mode=telegram.ParseMode.HTML)
    elif action == "gender":
        if value == "Meidschi":
            command = "UPDATE users SET is_female = 1 WHERE id = {}".format(user_id)
            execute_command(db_file, command)
            bot.send_message(user_id, "Ok, du besch jetzt es {}".format(value), parse_mode=telegram.ParseMode.HTML)
        elif value == "Bueb":
            command = "UPDATE users SET is_female = 0 WHERE id = {}".format(user_id)
            execute_command(db_file, command)
            bot.send_message(user_id, "Ok, du besch jetzt en {}".format(value), parse_mode=telegram.ParseMode.HTML)
        else:
            command = "UPDATE users SET is_female = 0 WHERE id = {}".format(user_id)
            execute_command(db_file, command)
            bot.send_message(user_id, "Ok, wenn du meinsch.".format(value), parse_mode=telegram.ParseMode.HTML)
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
    choices = [["1h", "10:00"], ["1w", "∞"], ["Promille"]]
    show_keyboard(bot, update, choices, "highscore", "Wie lang?")


def get_best(min_timestamp):
    command = "SELECT SUM(consumptions.amount*drinks.vol),users.name,users.id FROM consumptions JOIN users ON consumptions.user_id = users.id JOIN drinks on consumptions.drink_id = drinks.id WHERE consumptions.ts > {} and deleted = 0 GROUP BY consumptions.user_id ORDER BY SUM(consumptions.amount*drinks.vol) DESC;".format(min_timestamp)
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


def promille(bot, update):
    promille, relevant_amount = promille_rechner(update.message.from_user.id)
    if promille is None:
        bot.send_message(update.message.from_user.id,
                         "Ech bruuche dis gwecht, gschlächt ond dini grössi för das.\n/weight\n/height\n/gender",
                         parse_mode=telegram.ParseMode.HTML)
    else:
        bot.send_message(update.message.from_user.id,
                         "Du hesch momentan {:.2f}‰ wäg {:.1f}l Bier.".format(promille, relevant_amount / 5),
                         parse_mode=telegram.ParseMode.HTML)


def promille_rechner(user_id):
    command = "SELECT height,weight,is_female,name from users WHERE id = {};".format(user_id)
    height, weight, is_female, name = execute_command(db_file, command)[0]

    print(height, weight, is_female)

    if height is None or weight is None or is_female is None:
        return None, None

    if is_female:
        koeff = 1.055 * (-2.097 + 0.1069 * height + 0.2466 * weight) / (0.8 * weight)
    else:
        koeff = 1.055 * (2.447 - 0.09516 * 23 + 0.1074 * height + 0.3362 * weight) / (0.8 * weight)

    print(koeff)
    command = "SELECT ts, amount, drinks.vol FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and consumptions.deleted = 0 ORDER BY consumptions.ts ASC".format(user_id)
    drinks = execute_command(db_file, command)

    last_promille = 0
    last_timestamp = 0
    relevant_amount = 0
    time_promille = []
    for timestamp, amount, vol in drinks:
        alkohol_g = amount * 0.8 * vol / 100
        bak_theoretisch = alkohol_g / (weight * koeff)
        bak_resorbiert = bak_theoretisch - (bak_theoretisch * .15)
        time_since_last = (timestamp - last_timestamp) / (60 * 60)
        last_promille = max(0, last_promille - time_since_last * 0.0001)
        if last_promille == 0:
            relevant_amount = 0
        last_promille += bak_resorbiert
        relevant_amount += amount * vol
        last_timestamp = timestamp
        time_promille.append((last_timestamp, last_promille))
        print("{} {:%d.%m %H:%M:%S} {:.5f} {:.5f}".format(name, datetime.fromtimestamp(timestamp), bak_resorbiert * 1000, last_promille * 1000))

    timestamp_now = datetime.timestamp(datetime.now())
    time_since_last = (timestamp_now - last_timestamp) / (60 * 60)

    promille_now = max(0, last_promille - time_since_last * 0.0001)
    if promille_now == 0:
        relevant_amount = 0
    time_promille.append((timestamp_now, promille_now))

    return max(0, last_promille - time_since_last * 0.0001) * 1000, relevant_amount


def start(bot, update):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    command = "INSERT INTO users (id,name) VALUES ({}, '{}');".format(user_id, user_name)
    execute_command(db_file, command)
    bot.send_message(update.message.from_user.id,
                     text="Welcome to Zapfen Bot. These are the commands I know:\n" + instructions(),
                     parse_mode=telegram.ParseMode.HTML)


db_file = "zapfen.db"
drink_ids = {"bier": 0, "cocktail": 1, "shot": 2, "wein": 3}
available_commands = {"zapfen": (zapfen, "Zapf es getränk!"),
                      "highscore": (highscore, "Wer zapft am fliisigste?"),
                      "delete": (delete, "Falls eis z'vell gsi esch."),
                      "undelete": (undelete, "Falls es doch ned z'vell gsi esch."),
                      "promille": (promille, "Rächnet der us wie vell promille du hesch."),
                      "gender": (get_gender, "För de Promillerächner."),
                      "weight": (get_weight, "För de Promillerächner."),
                      "height": (get_height, "För de Promillerächner."),
                      }

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
