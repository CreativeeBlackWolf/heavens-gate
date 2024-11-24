import re
from datetime import timedelta
from typing import Optional


# thanks to: https://stackoverflow.com/a/4628148
def parse_time(time: str) -> Optional[timedelta]:
    """
    Parses a time string and returns a timedelta object.
    The time string can include days, weeks, months, and years, specified as:
    - 'd' for days
    - 'w' for weeks
    - 'M' for months (30 days each)
    - 'Y' for years (365 days each)

    For example, the string "2d3w1M" would be parsed as 2 days, 3 weeks, and 1 month.
    Args:
        time (str): The time string to parse.
    Returns:
        Optional[timedelta]: A timedelta object representing the parsed time, or None if the input string is invalid.
    """
    regex = re.compile(r"((?P<days>\d+?)d)?((?P<weeks>\d+?)w)?((?P<months>\d+?)M)?((?P<years>\d+?)Y)?")

    parts = regex.match(time)
    if not parts:
        return None

    if parts.lastindex is None:
        return None

    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            if name == "months":
                time_params["days"] = int(param) * 30
            elif name == "years":
                time_params["days"] = int(param) * 365
            else:
                time_params[name] = int(param)
    parsed_time = timedelta(**time_params)
    return parsed_time if parsed_time != timedelta(0) else None
