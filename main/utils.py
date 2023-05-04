from os import linesep
from typing import Iterator


def smart_split(string: str, length_limit: int) -> Iterator[str]:
    """
    A utility method that splits a string up into substrings no longer than the given limit, but tries to split the
    strings around line breaks, sentence breaks, or spaces.
    :param string: The string to split.
    :param length_limit: The length limit of substrings.
    :return: A generator of the split substrings.
    """
    remaining_string = string
    while len(remaining_string) > length_limit:
        substring, remaining_string = remaining_string[:length_limit], remaining_string[length_limit:]

        for separator in [linesep + linesep, linesep, '. ', ' ']:
            if separator in substring:
                (final_substring, extra_remainder) = substring.rsplit(separator, 1)
                if separator == '. ':
                    final_substring += '.'
                yield final_substring
                remaining_string = extra_remainder + remaining_string
                break
        else:
            yield substring

    yield remaining_string
