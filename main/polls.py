import shlex
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional

import discord
from dateutil.parser import parser
from discord import Message
from discord_slash import SlashContext

import utils

YES = "🍏"
MAYBE = "🤨"
UNLIKELY = "🥶"
NO = "🚫"
MULTIPOLL_EMOJIS = [YES, MAYBE, UNLIKELY, NO]
MULTIPOLL_QUESTION_PREFIX = "New poll: "
MULTIPOLL_HELP_TEXT = \
    f"Click one reaction on each poll option. {YES} = Yes, {MAYBE} = Maybe, {UNLIKELY} = Likely Not, {NO} = No"


async def multipoll(ctx: SlashContext, question: str, options: str):
    poll_options = shlex.split(options)

    await post_multipoll(ctx, question, poll_options)


async def scheduling_multipoll(ctx: SlashContext, question: str, start_date_str: str = None, end_date_str: str = None):
    dates = get_scheduling_dates(end_date_str, start_date_str)

    # Add multiple poll options for weekend dates
    poll_options = [option for sublist in map(lambda d: get_options_for_date(d), dates) for option in sublist]

    await post_multipoll(ctx, question, poll_options)


async def post_multipoll(ctx: SlashContext, question: str, poll_options: [str]):
    poll_question = MULTIPOLL_QUESTION_PREFIX + question

    # Send question message, options messages, and help text message
    sent_messages = await utils.send_multiple_replies(ctx, [poll_question] + poll_options + [MULTIPOLL_HELP_TEXT])

    # Add emoji reactions
    option_messages = sent_messages[1:-1]
    for emoji in MULTIPOLL_EMOJIS:
        for message in option_messages:
            await message.add_reaction(emoji)


def get_scheduling_dates(end_date_str: str = None, start_date_str: str = None) -> [date]:
    if start_date_str is None:
        start_date = get_next_monday()
    else:
        start_date = parser().parse(start_date_str).date()

    if end_date_str is None:
        # Default poll duration to cover 1 week
        end_date = start_date + timedelta(days=6)
    else:
        end_date = parser().parse(end_date_str).date()

    num_days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=i) for i in range(num_days)]


def get_options_for_date(date: date) -> [str]:
    day_name = date.strftime("%A")
    date_string = f"{day_name} {date.month}/{date.day}"

    # Include morning options for weekends.
    if date.weekday() >= 5:
        yield "🌅 " + date_string

    yield "🌃 " + date_string


def get_next_monday() -> date:
    today = date.today()
    days_until_monday = (0 - today.weekday()) % 7
    return today + timedelta(days=days_until_monday)


async def multipoll_results(ctx: SlashContext, ranking_mode: str, result_limit: int):
    await ctx.send("Fetching multipoll results...", hidden=True)

    ranking_mode_enum = ResultRankingMode[ranking_mode]

    last_multipoll = await find_multipoll(ctx, ranking_mode_enum)
    if not last_multipoll:
        return

    poll_options_by_score = last_multipoll.poll_options_by_score()

    embed = discord.Embed(
        title="Poll Results",
        description=last_multipoll.question(),
        color=discord.Color.gold(),
    )
    rank = 1
    for score in sorted(poll_options_by_score.keys(), reverse=True):
        tied_poll_options = sorted(poll_options_by_score[score], key=lambda p: p.name)
        for poll_option in tied_poll_options:
            embed.add_field(name="\n" + str(rank) + ". " + poll_option.name, value="> " + poll_option.emoji_str(),
                            inline=False)

        rank += len(tied_poll_options)
        if rank > result_limit:
            break

    embed.set_footer(text=f"Ranking mode: {ranking_mode}")

    await ctx.channel.send(embed=embed, reference=last_multipoll.question_message)


class ResultRankingMode(Enum):
    SCORE = {YES: 3, MAYBE: 1, UNLIKELY: -1, NO: -3}
    MOST_GOOD = {YES: 100, MAYBE: 10, UNLIKELY: 1, NO: -0.1}
    LEAST_BAD = {YES: 0.1, MAYBE: -1, UNLIKELY: -10, NO: -100}


class MultipollResult:
    def __init__(self, poll_option: Message, ranking_mode: ResultRankingMode):
        self.name = poll_option.content
        self.ranking_mode = ranking_mode

        self.yes = self.count_reaction(poll_option, YES)
        self.maybe = self.count_reaction(poll_option, MAYBE)
        self.unlikely = self.count_reaction(poll_option, UNLIKELY)
        self.no = self.count_reaction(poll_option, NO)

        self.score = self.ranking_mode.value[YES] * self.yes \
                     + self.ranking_mode.value[MAYBE] * self.maybe \
                     + self.ranking_mode.value[UNLIKELY] * self.unlikely \
                     + self.ranking_mode.value[NO] * self.no

    def __str__(self):
        return self.name + f" [Score: {self.score}] " + self.emoji_str()

    def __lt__(self, other):
        return self.score.__lt__(other.score)

    def emoji_str(self):
        return YES * self.yes + MAYBE * self.maybe + UNLIKELY * self.unlikely + NO * self.no

    @staticmethod
    def count_reaction(message: Message, emoji: str):
        for reaction in message.reactions:
            if reaction.emoji == emoji:
                return reaction.count - 1  # This bot added all the reactions.
        return 0


class Multipoll:
    def __init__(self, question_message: Message, poll_option_messages: [Message], ranking_mode: ResultRankingMode):
        self.question_message = question_message
        self.poll_options = map(lambda msg: MultipollResult(msg, ranking_mode), poll_option_messages)

    def question(self) -> str:
        return self.question_message.content[len(MULTIPOLL_QUESTION_PREFIX):]

    def poll_options_by_score(self) -> {}:
        poll_options_by_score = {}

        for poll_option in self.poll_options:
            score = poll_option.score
            if score not in poll_options_by_score:
                poll_options_by_score[score] = []
            poll_options_by_score.get(score).append(poll_option)

        return poll_options_by_score


async def find_multipoll(ctx: SlashContext, ranking_mode: ResultRankingMode) -> Optional[Multipoll]:
    poll_options = []
    found_multipoll = False
    question = None
    async for message in ctx.channel.history(limit=200):
        if message.author != ctx.me:
            continue

        if not found_multipoll:
            if message.content == MULTIPOLL_HELP_TEXT:
                # print("Found multipoll: " + message.content)
                found_multipoll = True
        else:
            if message.content.startswith(MULTIPOLL_QUESTION_PREFIX):
                question = message
                # print("Found multipoll question: " + message.content)
                break
            else:
                # print("Found multipoll option: " + message.content)
                poll_options.append(message)

    # Verify the question was found.
    if not found_multipoll or not question:
        await ctx.channel.send("Could not find recent multipoll.", delete_after=5)
        return None

    return Multipoll(question_message=question, poll_option_messages=poll_options, ranking_mode=ranking_mode)
