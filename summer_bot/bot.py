import datetime
import logging
import random
from textwrap import dedent

from simple_settings import settings

from telegram.ext import Updater, CommandHandler
import pytz
import emoji

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def get_days_left_in_summer(tz=None):
    utcnow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    if tz is None:
        tz = settings.DEFAULT_TIMEZONE
    tznow = utcnow.astimezone(pytz.timezone(tz))
    tznow_date = tznow.date()
    first_day = datetime.date(tznow_date.year, 6, 1)
    last_day = datetime.date(tznow_date.year, 9, 1)
    if first_day <= tznow_date <= last_day:
        return (last_day - tznow_date).days
    else:
        return 0

RESPONSES = '''\
It is certain
It is decidedly so
Without a doubt
Yes definitely
You may rely on it
As I see it, yes
Most likely
Outlook good
Yes
Signs point to yes
Reply hazy try again
Ask again later
Better not tell you now
Cannot predict now
Concentrate and ask again
Don't count on it
My reply is no
My sources say no
Outlook not so good
Very doubtful
'''.split('\n')


def start(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=dedent("""\
                Yo yo yo!!! I am summer bot and I can:
                /summerdays - I will write to the chat how many days left
                /magicball - Ask me something
                """
            )
        )


def magic_8_ball(bot, update):
    answer = random.choice(RESPONSES)
    bot.send_message(
            chat_id=update.message.chat_id,
            reply_to_message_id=update.message.message_id,
            text=answer
            )


def days_left(bot, update):
    days_left = get_days_left_in_summer()
    if days_left == 0:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=(
                'лето кончилось :('
                )
            )
        return
    days_left_100 = days_left % 100
    days_left_10 = days_left % 10
    if (
            (days_left_100 < 10 or days_left_100 > 20) and
            1 <= days_left_10 < 5
             ):
        if days_left_10 == 1:
            days_text = '{}день'.format(days_left)
        else:
            days_text = '{}дня'.format(days_left)
    else:
        days_text = '{}дней'.format(days_left)
    bot.send_message(
        chat_id=update.message.chat_id,
        text=(
            '#ровноцелых{} 🌞'.format(days_text)
            )
        )


def main():
    updater = Updater(token=settings.API_KEY)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    days_handler = CommandHandler('summerdays', days_left)
    dispatcher.add_handler(days_handler)

    magic_ball_handler = CommandHandler('magicball', magic_8_ball)
    dispatcher.add_handler(magic_ball_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()
