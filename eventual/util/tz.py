import datetime as dt

import pytz


def tz_aware_utcnow() -> dt.datetime:
    return dt.datetime.now(tz=pytz.UTC)
