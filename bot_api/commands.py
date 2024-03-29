from argparse import ArgumentParser
import datetime
from typing import Optional

from sqlalchemy.orm import Session
import dateparser

from bot_api import crud
from bot_api.errors import (
    AlreadyCancelledError,
    AlreadyClearedError,
    AlreadyScheduledError,
    ArgumentError,
    ExistingDateError,
    InvalidDateError,
    InvalidEventError,
    MissingDateError,
    PastDateError,
    UsageError,
)
from bot_api.models import Event


event_types = ["fagdag", "formiddag"]
default_responses = {
    "NO_EVENTS": "No upcoming events.",
    "INVALID_DATE_ERROR": "Error: Unable to parse date.",
    "EXISTING_DATE_ERROR": "Error: Date already in schedule",
    "PAST_DATE_ERROR": "Error: Date is in the past.",
    "INVALID_EVENT_ERROR": f"Error: Invalid event. Try one of {event_types}",
    "SCHEDULE_EMPTY_ERROR": "Error: The upcoming schedule is empty. Please add some dates.",
    "MISSING_DATE_ERROR": (
        "Error: The specified date is not in the schedule. Use the `add` command if you want to add a new date."
    ),
    "ALREADY_CANCELLED_ERROR": "Error: This event has (already) been cancelled.",
    "ALREADY_CLEARED_ERROR": "Error: This event is already empty.",
    "ALREADY_SCHEDULED_ERROR": "Error: A presentation has already been scheduled on this date.",
    "CALL_TO_ACTION": "No one is scheduled for the next presentation ({0}). The due date is *{1}* at 23:59.",
}


class CustomArgumentParser(ArgumentParser):
    def error(self, message):
        raise ArgumentError(message)
        # self.exit(2, '%s: error: %s\n' % (self.prog, message))


def prettify_date(date):
    return date.strftime("%a %-d %b")


def get_formatted_event(event: Event):
    is_fagdag = str(event.event_type) == "fagdag"

    if event.what is None:
        response = f"*{prettify_date(event.when)}*: No presentation scheduled."
    elif event.who is None:
        return f"*{prettify_date(event.when)}*: Event is cancelled due to {event.what}!"
    else:
        response = f"*{prettify_date(event.when)}*: Presentation *{event.what}* by *{event.who}*."

    fagdag_tag = " :busts_in_silhouette: Fagdag" if is_fagdag else ""
    return f"{response}{fagdag_tag}"


def get_args_from_request(request):
    """Creates an ArgumentParser and parses input arguments"""
    cmd_parser = CustomArgumentParser()

    cmd_parser.add_argument("command", type=str)

    cmd_parser.add_argument("--who", nargs="+", type=str)
    cmd_parser.add_argument("--what", nargs="+", type=str)
    cmd_parser.add_argument("--when", nargs="+", type=str)
    cmd_parser.add_argument("--event", type=str)
    cmd_parser.add_argument("--silent", "-s", action="store_true")

    args = cmd_parser.parse_args(request.split())

    # Combine list input into space separated strings
    args.who = " ".join(args.who).replace('"', "") if args.who else None
    args.what = " ".join(args.what).replace('"', "") if args.what else None
    args.when = " ".join(args.when).replace('"', "") if args.when else None

    return args


def schedule_new_event(args, db: Optional[Session] = None):
    if not args.who or not args.when or not args.what:
        raise UsageError

    when = dateparser.parse(args.when)
    if not when:
        raise InvalidDateError

    when = when.date()
    db_event = crud.get_closest_event(db, when=when)
    if not db_event:
        raise MissingDateError

    when = db_event.when
    if datetime.datetime.now().date() > when:
        raise PastDateError

    if db_event.what and db_event.who:
        raise AlreadyScheduledError

    if db_event.what:
        raise AlreadyCancelledError

    crud.update_event(db=db, db_event=db_event, what=args.what, who=args.who)

    return f"Successfully scheduled {get_formatted_event(db_event)}"


def clear_event(args, db: Optional[Session] = None):
    if not args.when:
        raise UsageError

    when = dateparser.parse(args.when)
    if not when:
        raise InvalidDateError

    when = when.date()
    db_event = crud.get_event_by_date(db, when=when)
    if not db_event:
        raise MissingDateError

    if datetime.datetime.now().date() > when:
        raise PastDateError

    if not bool(db_event.what) and not bool(db_event.who):
        raise AlreadyClearedError

    crud.update_event(db=db, db_event=db_event, what=None, who=None)

    return f"Successfully cleared {prettify_date(when)}"


def cancel_event(args, db: Optional[Session] = None):
    if not args.when or not args.what:
        raise UsageError

    when = dateparser.parse(args.when)
    if not when:
        raise InvalidDateError

    when = when.date()
    db_event = crud.get_event_by_date(db, when=when)
    if not db_event:
        raise MissingDateError

    if datetime.datetime.now().date() > when:
        raise PastDateError

    if bool(db_event.what) and not bool(db_event.who):
        raise AlreadyCancelledError

    crud.update_event(db=db, db_event=db_event, what=args.what, who=None)

    return f"Successfully cancelled {get_formatted_event(db_event)}"


def add_new_date(args, db: Session = None):
    if not args.event or not args.when:
        raise UsageError

    when = dateparser.parse(args.when, settings={"STRICT_PARSING": True})

    if args.event not in event_types:
        raise InvalidEventError

    if not when:
        raise InvalidDateError

    when = when.date()
    if datetime.datetime.now().date() > when:
        raise PastDateError

    db_event = crud.get_event_by_date(db, when=when)
    if db_event:
        raise ExistingDateError

    crud.create_event(db=db, event_type=args.event, when=when)

    return f"{prettify_date(when)} successfully added to the schedule."


def remove_existing_future_date(args, db: Optional[Session] = None):
    if not args.when:
        raise UsageError

    when = dateparser.parse(args.when, settings={"STRICT_PARSING": True})

    if not when:
        raise InvalidDateError

    when = when.date()
    if datetime.datetime.now().date() > when:
        raise PastDateError

    db_event = crud.get_event_by_date(db, when=when)
    if not db_event:
        raise MissingDateError

    crud.remove_event(db=db, when=when)

    return f"{prettify_date(when)} successfully removed from the schedule."


def list_next_event(args, db: Optional[Session] = None):
    db_event = crud.get_closest_event(db, when=datetime.date.today())
    if db_event is None or not db_event.who:
        return default_responses["NO_EVENTS"]

    return get_formatted_event(db_event)


def list_upcoming_events(args, db: Optional[Session] = None):
    db_events = crud.get_upcoming_events(db, when=datetime.date.today())
    if db_events is None:
        return default_responses["NO_EVENTS"]

    return "\n".join([f">{get_formatted_event(event)}" for event in db_events])


def list_shorthands(args, db: Optional[Session] = None):
    return "\n".join([f">{c}: `{s}`" for s, c in shorthands.items()])


def list_help(args, db: Optional[Session] = None):
    return "\n".join([f"{y['usage']}\n>{y['help_text']}\n" for _, y in commands.items()])


def get_unique_shorthand(i: int, key: str, short_keys: str, long_keys: str):
    """Gets the shortest sub-string of 'key' that is not in either 'long_keys' or 'short_keys'."""

    if i >= len(key):
        return key

    sh = key[:i]

    if sh in long_keys:
        return key

    if sh in short_keys or sh in long_keys:
        return get_unique_shorthand(i + 1, key, short_keys, long_keys)

    return sh


commands = {
    "next": {
        "command": list_next_event,
        "help_text": "Displays the next event.",
        "usage": "`/c next`",
    },
    "upcoming": {
        "command": list_upcoming_events,
        "help_text": "Lists all planned events.",
        "usage": "`/c upcoming`",
    },
    "schedule": {
        "command": schedule_new_event,
        "help_text": (
            "Lets you schedule a new event. "
            "The date you pick has to exist and be vacant. "
            "To add a new date, see the `add` command. "
            "In order to cancel an event, see the `cancel` command. "
            "(Pro-tip: you don't have to specify an exact date – `in two weeks` and `13 nov` works just as well!)"
        ),
        "usage": "`/c schedule --who <who> --what <what> --when <when>`",
    },
    "add": {
        "command": add_new_date,
        "help_text": (
            f"Adds a new (empty) date to the schedule of type <event>. "
            f"Allowed event types: "
            f"{', '.join([f'`{x}`' for x in event_types])}"
        ),
        "usage": "`/c add --event <event> --when yyyy-mm-dd`",
    },
    "remove": {
        "command": remove_existing_future_date,
        "help_text": "Removes an existing date from the schedule.",
        "usage": "`/c remove --when yyyy-mm-dd`",
    },
    "help": {"command": list_help, "help_text": "Displays this help text.", "usage": "`/c help`"},
    "clear": {
        "command": clear_event,
        "help_text": "Clears both the current presenter and the topic (`who` and `what`) on the selected date.",
        "usage": "`/c clear --when yyyy-mm-dd`",
    },
    "cancel": {
        "command": cancel_event,
        "help_text": "Cancels the event on the specified date.",
        "usage": "`/c cancel --when yyyy-mm-dd --what <reason>`",
    },
    "shorthands": {
        "command": list_shorthands,
        "help_text": "Displays shorthand versions of the commands",
        "usage": "`/c shorthands`",
    },
}

shorthands = {}
for key in commands:
    shorthand = get_unique_shorthand(1, key, shorthands, commands)
    shorthands[shorthand] = key

default_responses["INVALID_COMMAND"] = f"Sorry. Try one of these: *{commands}*."
