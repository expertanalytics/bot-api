import datetime
from argparse import ArgumentParser

import pytest
from mock import Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from bot_api import main, commands, models, crud


client = TestClient(main.app)


def test_prettify_date():
    assert commands.prettify_date(datetime.datetime(2020,1,1)) == "Wed 1 Jan"
    assert commands.prettify_date(datetime.datetime(2020,5,7)) == "Thu 7 May"
    assert commands.prettify_date(datetime.datetime(2020,9,5)) == "Sat 5 Sep"


@pytest.fixture
def mock_event_fagdag():
    event = Mock(spec=models.Event)
    event.when = datetime.datetime(2020,5,7).date()
    event.event_type = "fagdag"
    event.who = None
    event.what = None
    return event


def test_get_formatted_event_cancelled_fagdag(mock_event_fagdag):
    mock_event_fagdag.what = "reason"

    event_str = commands.get_formatted_event(mock_event_fagdag)

    assert event_str == "*Thu 7 May*: Event is cancelled due to reason!"


def test_get_formatted_event_scheduled_fagdag(mock_event_fagdag):
    mock_event_fagdag.who = "Someone"
    mock_event_fagdag.what = "Something"

    event_str = commands.get_formatted_event(mock_event_fagdag)

    assert event_str == (
            "*Thu 7 May*: ""Presentation *Something* by *Someone*. "
            ":busts_in_silhouette: Fagdag")


def test_get_formatted_event_not_scheduled_fagdag(mock_event_fagdag):
    event_str = commands.get_formatted_event(mock_event_fagdag)

    assert event_str == (
            "*Thu 7 May*: No presentation scheduled. "
            ":busts_in_silhouette: Fagdag")


@pytest.fixture
def mock_event_formiddag():
    event = Mock(spec=models.Event)
    event.when = datetime.datetime(2020,5,7).date()
    event.event_type = "formiddag"
    event.who = None
    event.what = None
    return event


def test_get_formatted_event_cancelled_formiddag(mock_event_formiddag):
    mock_event_formiddag.what = "reason"

    event_str = commands.get_formatted_event(mock_event_formiddag)

    assert event_str == "*Thu 7 May*: Event is cancelled due to reason!"


def test_get_formatted_event_scheduled_formiddag(mock_event_formiddag):
    mock_event_formiddag.who = "Someone"
    mock_event_formiddag.what = "Something"

    event_str = commands.get_formatted_event(mock_event_formiddag)

    assert event_str == "*Thu 7 May*: ""Presentation *Something* by *Someone*."


def test_get_formatted_event_not_scheduled_formiddag(mock_event_formiddag):
    event_str = commands.get_formatted_event(mock_event_formiddag)

    assert event_str == "*Thu 7 May*: No presentation scheduled."


@pytest.fixture
def mock_parser():
    return Mock(spec=ArgumentParser)


@pytest.fixture
def mock_db():
    return Mock(spec=Session)


def test__nearest():
    dates = [
            datetime.datetime(2020,5,7).date(),
            datetime.datetime(2020,2,27).date(),
            datetime.datetime(2020,4,10).date(),
            datetime.datetime(2020,5,8).date(),
            datetime.datetime(2020,5,5).date(),
            datetime.datetime(2020,10,8).date(),
            ]

    items = []
    for d in dates:
        mock = Mock()
        mock.when = d
        items.append(mock)

    res = crud._nearest(items, datetime.datetime(2020,5,6).date())
    assert res.when == datetime.datetime(2020,5,7).date()

    res = crud._nearest(items, datetime.datetime(2020,5,7).date())
    assert res.when == datetime.datetime(2020,5,7).date()

    res = crud._nearest(items, datetime.datetime(2020,5,9).date())
    assert res.when == datetime.datetime(2020,5,8).date()

    res = crud._nearest(items, datetime.datetime(2020,5,6).date())
    assert res.when != datetime.datetime(2020,5,5).date()

    res = crud._nearest(items, datetime.datetime(2020,6,6).date())
    assert res.when == datetime.datetime(2020,5,8).date()

    res = crud._nearest(items, datetime.datetime(2020,8,28).date())
    assert res.when == datetime.datetime(2020,10,8).date()

    res = crud._nearest(items, datetime.datetime(2020,11,11).date())
    assert res.when == datetime.datetime(2020,10,8).date()

    res = crud._nearest(items, datetime.datetime(2030,11,11).date())
    assert res.when == datetime.datetime(2020,10,8).date()

    res = crud._nearest(items, datetime.datetime(2019,11,11).date())
    assert res.when == datetime.datetime(2020,2,27).date()
