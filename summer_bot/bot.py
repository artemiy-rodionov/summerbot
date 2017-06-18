import datetime
import logging
import random
from textwrap import dedent

from simple_settings import settings

from telegram.ext import Updater, CommandHandler, Job
import pytz

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

DEFAULT_TZ = pytz.timezone(settings.DEFAULT_TIMEZONE)


def tznow(tz=None):
    utcnow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    if tz is None:
        tz = DEFAULT_TZ
    else:
        tz = pytz.timezone(tz)
    return utcnow.astimezone(tz)


def get_days_left_in_summer(tz=None):
    tznow_date = tznow().date()
    first_day = datetime.date(tznow_date.year, 6, 1)
    last_day = datetime.date(tznow_date.year, 9, 1)
    if first_day <= tznow_date <= last_day:
        return (last_day - tznow_date).days
    else:
        return 0

RESPONSES_EN = '''\
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
Very doubtful\
'''.split('\n')

RESPONSES_ES = '''\
En mi opinión, sí
Es cierto
Es decididamente así
Probablemente
Buen pronóstico
Todo apunta a que sí
Sin duda
Sí
Sí - definitivamente
Debes confiar en ello
Respuesta vaga, vuelve a intentarlo
Pregunta en otro momento
Será mejor que no te lo diga ahora
No puedo predecirlo ahora
Concéntrate y vuelve a preguntar
No cuentes con ello
Mi respuesta es no
Mis fuentes me dicen que no
Las perspectivas no son buenas
Muy dudoso\
'''.split('\n')
RESPONSES_DE = '''\
'''.split('\n')

RESPONSES_RU = '''\
Бесспорно
Предрешено
Никаких сомнений
Определённо да
Можешь быть уверен в этом
Мне кажется — «да»
Вероятнее всего
Хорошие перспективы
Знаки говорят — «да»
Да
Пока не ясно, попробуй снова
Спроси позже
Лучше не рассказывать
Сейчас нельзя предсказать
Сконцентрируйся и спроси опять
Даже не думай
Мой ответ — «нет»
По моим данным — «нет»
Перспективы не очень хорошие
Весьма сомнительно\
'''.split('\n')
RESPONSES_MAX='иди на хуй'.split('\n')


def start(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=dedent("""\
                Yo yo yo!!! I am summer bot and I can:
                /summerdays - I will write to the chat how many days left
                /magicball - спроси меня
                /magicballen - ask me
                /magicballmax - спроси Макса
                /magicballes - pregunta a mí
                /magicballru - спроси меня
                """
            )
        )


def magic_8_ball(responses):
    def f(bot, update):
        answer = random.choice(responses)
        bot.send_message(
                chat_id=update.message.chat_id,
                reply_to_message_id=update.message.message_id,
                text='🎱 {}'.format(answer)
                )
    return f


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


def callback_1900(bot, job):
    bot.send_message(
            chat_id=settings.SVOBODA_CHAT_ID,
            text='Го в Свобода'
            )
    next_run = 24 * 60 * 60
    logging.info("next run in {} seconds".format(next_run))
    job.interval = next_run


def main():
    updater = Updater(token=settings.API_KEY)
    dispatcher = updater.dispatcher
    jq = updater.job_queue

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    days_handler = CommandHandler('summerdays', days_left)
    dispatcher.add_handler(days_handler)

    for postfix, responses in (
            ('en', RESPONSES_EN),
            ('es', RESPONSES_ES),
            ('ru', RESPONSES_RU),
            ('max', RESPONSES_MAX)
            ):
        dispatcher.add_handler(CommandHandler(
                'magicball{}'.format(postfix),
                magic_8_ball(responses)
                ))
    dispatcher.add_handler(CommandHandler(
            'magicball',
            magic_8_ball(RESPONSES_RU)
            ))

    if settings.SVOBODA_CHAT_ID:
        moscow_now = tznow()
        cb_time = datetime.time(19, 0)
        if moscow_now.time() > cb_time:
            day = moscow_now.date() + datetime.timedelta(days=1)
        else:
            day = moscow_now.date()
        cb_dtime = DEFAULT_TZ.localize(datetime.datetime.combine(day, cb_time))
        delta = cb_dtime - moscow_now
        logging.info('Cb dtime {} now is {}'.format(cb_dtime, moscow_now))
        logging.info('Set job after {} seconds'.format(delta.total_seconds()))
        jq.put(Job(callback_1900, delta.total_seconds()))

    updater.start_polling()


if __name__ == '__main__':
    main()
