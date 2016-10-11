import telebot
import re
import os
import operator
import ephem
import json
import csv
from datetime import datetime, date


bot = telebot.TeleBot(os.environ.get("TELETOKEN"))


def writelog(message):
    timestamp = datetime.fromtimestamp(message.date).strftime('%Y-%m-%d %H:%M:%S')
    line = '{0} {1}: \'{2}\'\n'.format(timestamp, message.from_user.username, message.text)
    with open('log', 'a') as logger:
        logger.write(line)


def writecsv(message):
    date = datetime.fromtimestamp(message.date).strftime('%Y-%m-%d')
    time = datetime.fromtimestamp(message.date).strftime('%H:%M:%S')
    log = [{'date': date, 'time': time, 'username': message.from_user.username, 'content': message.text}]
    with open('log.csv', 'a', encoding='utf-8') as logger:
        fields = [field for field in log[0].keys()]
        writer = csv.DictWriter(logger, fields, delimiter=';')
        if not os.path.isfile('log.csv'):
            writer.writeheader()
        writer.writerow(log[0])


def init_phrasebook():
    with open('answers.json', 'r') as json_data:
        return json.load(json_data)


def words_to_digits(expression):
    tokens = {'один': '1',
              'два': '2',
              'три': '3',
              'четыре': '4',
              'пять': '5',
              'шесть': '6',
              'семь': '7',
              'восемь': '8',
              'девять': '9',
              'плюс': '+',
              'минус': '-',
              'умножить': '*',
              'разделить': '/'
              }
    for token, value in tokens.items():
        expression = expression.replace(token, value)
    expression = expression.replace('и', '.')
    pattern = '(?:(?![0-9.\-*+=\/]).)*'
    expression = re.sub(pattern, '', expression)
    return expression + '='


@bot.message_handler(commands=['start'])
def send_welcome(message):
    writecsv(message)
    reply = bot.reply_to(message, 'Init1')
    writecsv(reply)
    reply


@bot.message_handler(commands=['count'])
def count_words(message):
    count = message.text.split(' ')
    bot.reply_to(message, len(count[1:]))


@bot.message_handler(func=lambda message: message.text.rstrip()[-1] == '=')
# TODO: Приоритет знаков
def calculate(message):
    expression = message.text.replace(' ', '')
    tokens = {'+': operator.add,
              '-': operator.sub,
              '*': operator.mul,
              '/': operator.truediv
              }
    pattern = '([0-9.]|\d[+\-*/]?)+(?<=\d)='
    if re.fullmatch(pattern, expression) is None:
        bot.reply_to(message, 'Похоже, вы допустили ошибку! Проверьте выражение и попробуйте ещё раз!')
        return
    digits = re.findall('[0-9.]+|\d+', expression)
    digits = [float(x) for x in reversed(digits)]
    operators = re.findall('[+\-*/]', expression)
    for op in operators:
        result = tokens[op](digits.pop(), digits.pop())
        if not digits:
            bot.reply_to(message, result)
        digits.append(result)


@bot.message_handler(func=lambda message: message.text.lower().startswith('сколько будет'))
def words_calculator(message):
    message.text = words_to_digits(message.text.lower())
    calculate(message)


@bot.message_handler(func=lambda message: 'полнолуние' in message.text.lower())
def next_newmoon(message):
    date = re.sub('[А-я]+\s+', '', message.text)
    if not date:
        bot.reply_to(message, 'Не забудьте написать дату!')
    reply = ephem.next_new_moon(date)
    bot.reply_to(message, reply)


@bot.message_handler(func=lambda message: re.sub('\W+', '', message.text.lower()) in ANSWERS)
def answer(message):
    phrase = re.sub('\W+', '', message.text)
    bot.reply_to(message, ANSWERS.get(phrase.lower()))
    bot.reply_to(message, message)


@bot.message_handler(func=lambda message: 'нового года' in message.text.lower())
def newyear_countdown(message):
    today = date.today()
    newyear = date(today.year + 1, 1, 1)
    result = newyear - today
    result = result.days
    if result % 100 in range(5, 21) or result % 100 == 0:
        days = 'дней'
    if result % 10 in range(5, 9) or result % 10 == 0:
        days = 'дней'
    if result % 10 == 1:
        days = 'день'
    if result % 10 in range(2, 5):
        days = 'дня'
    bot.reply_to(message, "До нового {0} года осталось {1} {2}.".format(newyear.year, result, days))


@bot.message_handler(func=lambda message: True)
def true(message):
    timestamp = datetime.fromtimestamp(message.date).strftime('%Y-%m-%d %H:%M:%S')
    msg = bot.send_message(message.chat.id, timestamp)
    bot.send_message(message.chat.id, msg)


if __name__ == '__main__':
    ANSWERS = init_phrasebook()
    bot.polling()
