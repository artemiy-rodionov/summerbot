import datetime
import calendar
import logging
import random
from textwrap import dedent
import sqlite3

from simple_settings import settings
import requests

from flask import Flask, redirect, url_for, request

from telegram.ext import (
    Updater, CommandHandler, Job, MessageHandler, BaseFilter, Filters
)

from instagram.client import InstagramAPI
import pytz

logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
logger = logging.getLogger(__name__)

TEL_JOB_QUEUE = None
DEFAULT_TZ = pytz.timezone(settings.DEFAULT_TIMEZONE)


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
SLABAK_STICKER_ID = 'CAADAgADGQADILtyA8fJUtBfJbTsAg'


# helpers


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


# end helpers


# db methods

def conn_db():
    conn = sqlite3.connect(settings.DB_PATH)
    return conn


def ts_utcnow():
    return calendar.timegm(datetime.datetime.utcnow().timetuple())


def create_db_tables():
    logger.info('Creating db tables')
    conn = conn_db()
    with conn:
        conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS insta_users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                access_token TEXT,
                instagram_id TEXT,
                created INT
                );
                '''
        )
        conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS insta_posts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instagram_id TEXT,
                user_id INT,
                data TEXT,
                posted INT,
                created INT
                );
                '''
        )


def register_user(token, user_data):
    logger.info('Registering user')
    conn = conn_db()
    name = user_data['username']
    with conn:
        cur = conn.cursor()
        cur.execute('SELECT id FROM insta_users WHERE name=?', (name,))
        data = cur.fetchone()
        if data is None:
            logger.info('Add new user {}'.format(name))
            cur.execute('INSERT INTO insta_users values (?,?,?,?,?)', (
                None, name, token, user_data['id'], ts_utcnow()
            ))
            is_new = True
        else:
            logger.info('Update user {}'.format(name))
            cur.execute('UPDATE insta_users SET access_token=? where id=?', (
                token, data[0]
            ))
            is_new = False
    return is_new


def add_new_instagram_post(insta_data):
    pass


# end db

# instagram methods


def get_insta_client(access_token=None):
    return InstagramAPI(
        client_id=settings.INSTAGRAM_CLIENT_ID,
        client_secret=settings.INSTAGRAM_CLIENT_SECRET,
        redirect_uri=url_for('instagram_success', _external=True),
        access_token=access_token
    )


def post_last_photo(name):
    conn = conn_db()
    with conn:
        cur = conn.cursor()
        cur.execute('SELECT access_token, instagram_id FROM insta_users WHERE name=?', (name,))
        data = cur.fetchone()
        if not data:
            return
        api = get_insta_client(access_token=data[0])
        recent_media, next_ = api.user_recent_media(user_id=data[1], count=1)
        for media in recent_media:
            url = media.get_standard_resolution_url()
            logger.info('Last url {}'.format(url))
            TEL_JOB_QUEUE.put(Job(post_image_url, 1, repeat=False, context=url))


# end instagram

# http server

app = Flask(__name__)

@app.route('/')
def yo():
    return 'yo'


@app.route('/instagram_connect/')
def instagram_connect():
    api = get_insta_client()
    return redirect(api.get_authorize_login_url())


@app.route('/instagram_hook/', methods=['GET', 'POST'])
def instagram_hook():
    logger.info(request.args)
    logger.info(request.data)
    challenge = request.args.get('hub.challenge')
    if challenge:
        return challenge, 200
    return 'ok', 200


@app.route('/instagram_success/', methods=['GET', 'POST'])
def instagram_success():
    code = request.args.get('code')
    error = request.args.get('error')
    if error:
        return ':( {}'.format(request.args.get('error_decription')), 200
    if code:
        api = get_insta_client()
        resp = requests.post(
            api.access_token_url,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                "client_id": api.client_id,
                "client_secret": api.client_secret,
                "redirect_uri": api.redirect_uri,
                "grant_type": "authorization_code",
                "code": code
            }
        )
        resp.raise_for_status()
        data = resp.json()
        user = data['user']
    logger.info(data)
    is_new = register_user(data['access_token'], user)
    if True or is_new:
        post_last_photo(user['username'])
        api.create_subscription(
            object='user',
            aspect='media',
            callback_url=url_for('instagram_hook', _external=True)
        )

    user_text = '''
            <h2>Yo, {username}!!</h2>
            <img src="{profile_picture}">
            <p>
            Last photo will soon be in chateg.
            </p>
            <i>Yoohoo, go svoboda now</i>
            '''.format(**user)
    return user_text, 200


def gen_url_for(*args, **kwargs):
    with app.app_context():
        return url_for(*args, **kwargs)


def run_http():
    app.config.update(settings.as_dict())
    app.debug = False
    app.use_reloader = False
    logger.info('Starting http server')
    app.run(host=settings.HTTP_HOST, port=settings.HTTP_PORT)


# end http server


# bot commands

def start(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=dedent(
            """\
            Yo yo yo!!! I am summer bot and I can:
            /summerdays - I will write to the chat how many days left
            /magicball - спроси меня
            /magicballen - ask me
            /magicballmax - спроси Макса
            /magicballes - pregunta a mí
            /magicballru - спроси меня
            /instagram - постить свои фоточки из инстаграма
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


def slabak_message(bot, update):
    bot.send_sticker(
        chat_id=update.message.chat_id,
        reply_to_message_id=update.message.message_id,
        sticker=SLABAK_STICKER_ID
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

def instagram_bot(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text='<a href="{url}">URL</a>'.format(
            url=gen_url_for('instagram_connect', _external=True)
        ),
        parse_mode=telegram.ParseMode.HTML
        )


def post_image_url(bot, job):
    bot.send_photo(
            chat_id=settings.SVOBODA_CHAT_ID,
            photo=job.context
            )


def callback_1900(bot, job):
    bot.send_message(
            chat_id=settings.SVOBODA_CHAT_ID,
            text='Го в Свобода'
            )
    next_run = 24 * 60 * 60
    logger.info("next run in {} seconds".format(next_run))
    job.interval = next_run


# end bot commands

def init_app():
    logger.info('Initing app')
    create_db_tables()


def main():
    init_app()

    logger.info('Starting app')

    updater = Updater(token=settings.API_KEY)
    dispatcher = updater.dispatcher
    global TEL_JOB_QUEUE
    TEL_JOB_QUEUE = updater.job_queue

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
<<<<<<< HEAD
    dispatcher.add_handler(
        MessageHandler(Filters.text & SlabakFilter(), slabak_message)
    )
||||||| merged common ancestors
=======
    dispatcher.add_handler(CommandHandler(
        'instagram',
        instagram_bot
        ))
>>>>>>> Add instagram handler

    if settings.SVOBODA_CHAT_ID:
        moscow_now = tznow()
        cb_time = datetime.time(19, 0)
        if moscow_now.time() > cb_time:
            day = moscow_now.date() + datetime.timedelta(days=1)
        else:
            day = moscow_now.date()
        cb_dtime = DEFAULT_TZ.localize(datetime.datetime.combine(day, cb_time))
        delta = cb_dtime - moscow_now
        logger.info('Cb dtime {} now is {}'.format(cb_dtime, moscow_now))
        logger.info('Set job after {} seconds'.format(delta.total_seconds()))
        TEL_JOB_QUEUE.put(Job(callback_1900, delta.total_seconds()))

    updater.start_polling(poll_interval=0.7)

    updater._init_thread(run_http, 'webserver')


if __name__ == '__main__':
    main()
