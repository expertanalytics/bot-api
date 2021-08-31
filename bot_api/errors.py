class UsageError(Exception):
    pass


class InvalidEventError(Exception):
    pass


class InvalidDateError(Exception):
    pass


class PastDateError(Exception):
    pass


class MissingDateError(Exception):
    pass


class AlreadyScheduledError(Exception):
    pass


class AlreadyClearedError(Exception):
    pass


class AlreadyCancelledError(Exception):
    pass


class ExistingDateError(Exception):
    pass


class ArgumentError(Exception):
    pass
