import enum


class Guarantee(str, enum.Enum):
    NO_MORE_THAN_ONCE = "NO_MORE_THAN_ONCE"
    EXACTLY_ONCE = "EXACTLY_ONCE"
    AT_LEAST_ONCE = "AT_LEAST_ONCE"
