import re
import datetime
import logging
import random
from textwrap import dedent

from simple_settings import settings

import telegram
from telegram.ext import (
    Updater, CommandHandler, Job, MessageHandler, BaseFilter, Filters
)

import pytz

logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

DEFAULT_TZ = pytz.timezone(settings.DEFAULT_TIMEZONE)


class ChatUserRegistry:
    def __init__(self):
        self._registry = {}

    def add_user(self, user, chat):
        if user.is_bot:
            return
        chat_id = chat.id
        if chat_id not in self._registry:
            logging.info(
                'Create new user chat registry {} {}'.format(
                    chat_id, chat.title)
            )
            self._registry[chat_id] = {}

        user_id = user.id
        if user_id not in self._registry[chat_id]:
            logging.info(
                'Add new user to chat registry {} {}'.format(chat, user)
            )
            self._registry[chat_id][user_id] = {
                'user_id': user_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        self._registry[chat_id][user_id]['last_message'] = tznow()

    def get_all_chat_users(self, chat):
        return self._registry.get(chat.id, {}).values()

    def get_active_users(self, chat, minutes=60):
        now = tznow()
        for user in self.get_all_chat_users(chat):
            since_last_message = now - user['last_message']
            if (since_last_message.total_seconds()) / 60 <= minutes:
                yield user


CHAT_USER_REGISTRY = ChatUserRegistry()


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

RESPONSES_MAX = 'иди на хуй'.split('\n')

SLABAK_TEXT = '''
пас
я пас\
'''.split('\n')

THREE_HUNDRED_TEXT = (
    '300',
    'триста'
)

SLABAK_STICKER_ID = 'CAADAgADGQADILtyA8fJUtBfJbTsAg'
TRAKTORIST_AUDIO_ID = 'AwADAgADOQIAAviVYEuJrf_4XXXKaAI'
CHANNEL_CMD = '@channel'
HERE_CMD = '@here'


def tznow(tz=None):
    utcnow = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    if tz is None:
        tz = DEFAULT_TZ
    else:
        tz = pytz.timezone(tz)
    return utcnow.astimezone(tz)


def get_days_left_in_summer(tz=None):
    tznow_date = tznow(tz=tz).date()
    first_day = datetime.date(tznow_date.year, 6, 1)
    last_day = datetime.date(tznow_date.year, 9, 1)
    if first_day <= tznow_date < last_day:
        return (last_day - tznow_date).days
    else:
        return 0


def get_days_till_summer(tz=None):
    tznow_date = tznow(tz=tz).date()
    first_day = datetime.date(tznow_date.year, 6, 1)
    last_day = datetime.date(tznow_date.year, 9, 1)
    if tznow_date < first_day:
        return (first_day - tznow_date).days
    elif first_day <= tznow_date < last_day:
        return 0
    else:
        first_day_next = datetime.date(tznow_date.year + 1, 6, 1)
        return (first_day_next - tznow_date).days


def get_days_till_ny(tz=None):
    tznow_date = tznow(tz=tz).date()
    ny_day = datetime.date(tznow_date.year+1, 1, 1)
    return (ny_day - tznow_date).days


def start(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=dedent(
            """\
            Yo yo yo!!! I am summer bot and I can:
            /summerdays - I will write to the chat how many days left
            /tillsummer - How many days till summer
            /magicball - спроси меня
            /magicballen - ask me
            /magicballmax - спроси Макса
            /magicballes - pregunta a mí
            /magicballru - спроси меня
            @channel - mention everyone
            @here - mention who was active in past hour
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


class SlabakFilter(BaseFilter):
    def filter(self, message):
        txt = message.text.strip().lower()
        return txt in SLABAK_TEXT


class ThreeHundredFilter(BaseFilter):
    def filter(self, message):
        txt = message.text.strip().lower()
        words = re.split('[\s,?!]', txt)
        return any(map(lambda opt: opt in words, THREE_HUNDRED_TEXT))


class ChannelFilter(BaseFilter):
    def filter(self, message):
        txt = message.text.lower().split()
        return CHANNEL_CMD in txt


class HereFilter(BaseFilter):
    def filter(self, message):
        txt = message.text.lower().split()
        return HERE_CMD in txt


def slabak_message(bot, update):
    bot.send_sticker(
        chat_id=update.message.chat_id,
        reply_to_message_id=update.message.message_id,
        sticker=SLABAK_STICKER_ID
    )


def three_hundered_message(bot, update):
    bot.send_voice(
        chat_id=update.message.chat_id,
        reply_to_message_id=update.message.message_id,
        voice=TRAKTORIST_AUDIO_ID,
        # caption='300',
    )


def all_message(bot, update):
    msg = update.message
    CHAT_USER_REGISTRY.add_user(msg.from_user, msg.chat)


def _mention_users(text, users):
    men_text = text
    for user in users:
        men_text = '[{}](tg://user?id={}) {}'.format(
            user['first_name'],
            user['user_id'],
            men_text
        )
    return men_text


def here_message(bot, update):
    text = update.message.text.replace(HERE_CMD, '')
    chat_users = CHAT_USER_REGISTRY.get_active_users(update.message.chat)
    text = _mention_users(text, chat_users)
    logging.info('here text: {}'.format(text))

    bot.send_message(
        chat_id=update.message.chat_id,
        text=text,
        parse_mode=telegram.ParseMode.MARKDOWN
    )


def channel_message(bot, update):
    text = update.message.text.replace(CHANNEL_CMD, '')
    chat_users = CHAT_USER_REGISTRY.get_all_chat_users(update.message.chat)
    logging.debug(chat_users)
    text = _mention_users(text, chat_users)
    logging.info('channel text: {}'.format(text))

    bot.send_message(
        chat_id=update.message.chat_id,
        text=text,
        parse_mode=telegram.ParseMode.MARKDOWN
    )


def _format_days(days_num):
    days_num_100 = days_num % 100
    days_num_10 = days_num % 10
    if (
        (days_num_100 < 10 or days_num_100 > 20) and
        1 <= days_num_10 < 5
    ):
        if days_num_10 == 1:
            days_text = '{}день'.format(days_num)
        else:
            days_text = '{}дня'.format(days_num)
    else:
        days_text = '{}дней'.format(days_num)
    return days_text


def days_till(bot, update):
    days_till = get_days_till_summer()
    if days_left == 0:
        bot.send_message(
            chat_id=update.message.chat_id,
            text=(
                'иди плавай'
                )
            )
        return
    emoji = '🌱'
    # '⛄'
    # '🍂'
    bot.send_message(
        chat_id=update.message.chat_id,
        text=(
            '#осталосьждать{} {}'.format(
                _format_days(days_till),
                emoji
            )
        )
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
    bot.send_message(
        chat_id=update.message.chat_id,
        text=(
            '#ровноцелых{} 🌞'.format(_format_days(days_left))
            )
        )


def days_message():
    days_left = get_days_left_in_summer()
    if days_left == 0:
        days_till_summer = get_days_till_summer()
        new_year_left = get_days_till_ny()
        if new_year_left < days_till_summer:
            emoji = random.choice((
                '🎅',
                '🦌',
                '🎄',
                "☃️'",
            ))
            if new_year_left == 1:
                emoji = '🎅'
            msg = '#{}доновогогода {}'.format(
                _format_days(new_year_left),
                emoji
            )
        else:
            emoji = '🌱'
            msg = '#осталосьждать{} {}'.format(
                _format_days(days_till_summer),
                emoji
            )
    else:
        msg = '#ровноцелых{} 🌞'.format(_format_days(days_left))
    return msg


def days_handler(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=days_message()
    )


def callback_svoboda(bot, job):
    bot.send_message(
            chat_id=settings.SVOBODA_CHAT_ID,
            text='Го в Свобода'
            )
    next_run = 24 * 60 * 60
    logging.info("next run in {} seconds".format(next_run))
    job.interval = next_run


def callback_summer(bot, job):
    msg = days_message()
    bot.send_message(
        chat_id=settings.SVOBODA_CHAT_ID,
        text=msg
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

    summerdays_handler = CommandHandler('summerdays', days_left)
    dispatcher.add_handler(summerdays_handler)

    tillsummer_handler = CommandHandler('tillsummer', days_till)
    dispatcher.add_handler(tillsummer_handler)

    days = CommandHandler('days', days_handler)
    dispatcher.add_handler(days)

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
    dispatcher.add_handler(
        MessageHandler(Filters.text & SlabakFilter(), slabak_message)
    )
    dispatcher.add_handler(
        MessageHandler(
            Filters.text & ThreeHundredFilter(),
            three_hundered_message)
    )
    dispatcher.add_handler(
        MessageHandler(Filters.text & ChannelFilter(), channel_message)
    )
    dispatcher.add_handler(
        MessageHandler(Filters.text & HereFilter(), here_message)
    )
    dispatcher.add_handler(
        MessageHandler(Filters.all, all_message)
    )

    def add_cb(cb_time, cb):
        moscow_now = tznow()
        if moscow_now.time() > cb_time:
            day = moscow_now.date() + datetime.timedelta(days=1)
        else:
            day = moscow_now.date()
        cb_dtime = DEFAULT_TZ.localize(datetime.datetime.combine(day, cb_time))
        delta = cb_dtime - moscow_now
        logging.info('Cb dtime {} now is {}'.format(cb_dtime, moscow_now))
        logging.info('Set job after {} seconds'.format(delta.total_seconds()))
        jq.put(Job(cb, delta.total_seconds()))

    if settings.SVOBODA_CHAT_ID:
        add_cb(datetime.time(19, 0), callback_svoboda)
        add_cb(datetime.time(12, 0), callback_summer)

    updater.start_polling()


if __name__ == '__main__':
    main()
