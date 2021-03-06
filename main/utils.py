from os import linesep
from typing import Iterator, Iterable

from discord import Message
from discord_slash import SlashContext


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


async def send_multiple_replies(ctx: SlashContext, messages: Iterable[str], delete_after: float = None) -> [Message]:
    iterator: Iterator[str] = iter(messages)

    # Send first message as a direct reply to the slash command.
    sent_messages = [await ctx.send(next(iterator), delete_after=delete_after)]

    # Send any further messages directly to the channel so the whole response is compactly spaced.
    for message in iterator:
        sent_messages.append(await ctx.channel.send(message, delete_after=delete_after))

    return sent_messages
