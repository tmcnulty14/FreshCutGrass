from os import linesep
from typing import Iterator, Optional, Callable, Union

from interactions import TYPE_ALL_CHANNEL, Message, Client, Member, User


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


async def find_matching_bot_message(channel: "TYPE_ALL_CHANNEL", bot: Client, message_limit: Optional[int] = None,
                                    match_condition: Callable[[Message], bool] = lambda message: True)\
        -> Optional[Message]:
    return await find_matching_message(channel, message_limit,
                                       lambda message: message.author == bot.user and match_condition(message))


async def find_matching_message(channel: "TYPE_ALL_CHANNEL", message_limit: int = 10,
                                match_condition: Callable[[Message], bool] = lambda message: True) -> Optional[Message]:
    history = channel.history(limit=message_limit)

    async for message in history:
        if match_condition(message):
            return message
    return None
