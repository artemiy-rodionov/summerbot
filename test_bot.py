import os

os.environ['SIMPLE_SETTINGS'] = 'summer_bot.config'

from freezegun import freeze_time

from summer_bot import bot



def test_summer_left(monkeypatch):
    with freeze_time('2017-06-03 12:00'):
        assert bot.get_days_left_in_summer() == 90
    with freeze_time('2017-08-31 12:00'):
        assert bot.get_days_left_in_summer() == 1
    with freeze_time('2017-09-01 12:00'):
        assert bot.get_days_left_in_summer() == 0
    with freeze_time('2017-03-01 12:00'):
        assert bot.get_days_left_in_summer() == 0
    with freeze_time('2017-06-01 12:00'):
        assert bot.get_days_left_in_summer() == 92


def test_summer_till(monkeypatch):
    with freeze_time('2017-06-03 12:00'):
        assert bot.get_days_till_summer() == 0
    with freeze_time('2017-08-31 12:00'):
        assert bot.get_days_till_summer() == 0
    with freeze_time('2017-09-01 12:00'):
        assert bot.get_days_till_summer() == 273
    with freeze_time('2017-03-01 12:00'):
        assert bot.get_days_till_summer() == 92
    with freeze_time('2017-06-01 12:00'):
        assert bot.get_days_till_summer() == 0


def test_ny_days(monkeypatch):
    with freeze_time('2017-12-30 12:00'):
        assert bot.get_days_till_ny() == 2
    with freeze_time('2017-12-31 1:00'):
        assert bot.get_days_till_ny() == 1
    with freeze_time('2017-01-01 12:00'):
        assert bot.get_days_till_ny() == 365


def test_day_message(monkeypatch):
    with freeze_time('2017-12-31 1:00'):
        assert 'доновогогода' in bot.days_message()
    with freeze_time('2017-03-01 12:00'):
        assert 'осталосьждать' in bot.days_message()
    with freeze_time('2017-08-31 12:00'):
        assert 'ровно' in bot.days_message()
