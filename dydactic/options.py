from enum import Enum


class ErrorOption(str, Enum):
    RETURN = 'return'
    RAISE = 'raise'
    SKIP = 'skip'