import shlex
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from dateutil.parser import parser
from interactions import AutoArchiveDuration, Extension, Message, OptionType, Role, SlashCommandChoice, SlashContext, \
    User, slash_command, slash_option

YES = "🍏"
MAYBE = "🤨"
UNLIKELY = "🥶"
NO = "🚫"
MULTIPOLL_EMOJIS = [YES, MAYBE, UNLIKELY, NO]
MULTIPOLL_QUESTION_PREFIX = "Poll: "
MULTIPOLL_HELP_TEXT = \
    f"Click one reaction on each poll option. {YES} = Yes, {MAYBE} = Maybe, {UNLIKELY} = Likely Not, {NO} = No"

FIRST = "🥇"
SECOND = "🥈"
THIRD = "🥉"
MEDALS = [FIRST, SECOND, THIRD]


class ResultRankingMode(Enum):
    SCORE = {YES: 3, MAYBE: 1, UNLIKELY: -1, NO: -3}
    MOST_GOOD = {YES: 100, MAYBE: 10, UNLIKELY: 1, NO: -0.1}
    LEAST_BAD = {YES: 0.1, MAYBE: -1, UNLIKELY: -10, NO: -100}


class PollsExtension(Extension):
    @slash_command(
        name="multipoll",
        description="Create a poll with multiple options.",
    )
    @slash_option(
        name="question",
        description="The poll question.",
        required=True,
        opt_type=OptionType.STRING,
    )
    @slash_option(
        name="options",
        description="The poll options, separated by spaces. Wrap with quotes to include a space in an option.",
        required=True,
        opt_type=OptionType.STRING,
    )
    @slash_option(
        name="mention_role",
        description="A role to mention.",
        required=False,
        opt_type=OptionType.ROLE,
    )
    async def multipoll(self, ctx: SlashContext, question: str, options: str, mention_role: Role = None):
        await multipoll(ctx, question, options, mention_role)

    @slash_command(
        name="schedule",
        description="Create a scheduling poll.",
    )
    @slash_option(
        name="question",
        description="The poll question.",
        required=True,
        opt_type=OptionType.STRING,
    )
    @slash_option(
        name="start_date",
        description="The start date of the scheduling range. Defaults to tomorrow.",
        required=False,
        opt_type=OptionType.STRING,
    )
    @slash_option(
        name="end_date",
        description="The end date of the scheduling range. Defaults to one week after the start date.",
        required=False,
        opt_type=OptionType.STRING,
    )
    @slash_option(
        name="mention_role",
        description="A role to mention.",
        required=False,
        opt_type=OptionType.ROLE,
    )
    async def schedule(self, ctx: SlashContext, question: str, start_date: str = None, end_date: str = None,
                       mention_role: Role = None):
        await scheduling_multipoll(ctx, question, start_date, end_date, mention_role)

    @slash_command(
        name="multipoll_results",
        description="Ranks the results of the last multipoll.",
    )
    @slash_option(
        name="ranking_mode",
        description="The mode to use for ranking results",
        opt_type=OptionType.STRING,
        required=False,
        choices=list(map(lambda ranking_mode_name: SlashCommandChoice(name=ranking_mode_name, value=ranking_mode_name),
                         ResultRankingMode.__members__.keys())),
    )
    async def multipoll_results(self, ctx: SlashContext, ranking_mode: str = ResultRankingMode.SCORE.name):
        await multipoll_results(ctx, ranking_mode)


def setup(bot):
    PollsExtension(bot)

async def multipoll(ctx: SlashContext, question: str, options: str, mention_role: Role = None):
    poll_options = shlex.split(options)

    await post_multipoll(ctx, question, poll_options, mention_role)


async def scheduling_multipoll(ctx: SlashContext, question: str, start_date_str: str = None, end_date_str: str = None,
                               mention_role: Role = None):
    dates = get_scheduling_dates(end_date_str, start_date_str)

    # Add multiple poll options for weekend dates
    poll_options = [option for sublist in map(lambda d: get_options_for_date(d), dates) for option in sublist]

    await post_multipoll(ctx, question, poll_options, mention_role)


async def post_multipoll(ctx: SlashContext, question: str, poll_options: [str], mention_role: Role = None):
    poll_question = MULTIPOLL_QUESTION_PREFIX + question
    if mention_role is not None:
        poll_question += " " + mention_role.mention

    # Send question message as a direct reply to the slash command, then turn it into a thread.
    sent_messages = [await ctx.send(poll_question)]
    thread = await ctx.channel.create_thread(name=poll_question,
                                             message=int(sent_messages[0]),
                                             auto_archive_duration=AutoArchiveDuration.THREE_DAY)

    # Send all further messages in the thread.
    option_messages = [await thread.send(option_message) for option_message in poll_options]
    await thread.send(MULTIPOLL_HELP_TEXT)

    # Add emoji reactions to the poll options.
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


async def multipoll_results(ctx: SlashContext, ranking_mode: str):
    ranking_mode_enum = ResultRankingMode[ranking_mode]

    last_multipoll = await find_multipoll(ctx, ranking_mode_enum)
    if not last_multipoll:
        await ctx.send("Could not find multipoll to rank.", ephemeral=True)
        return
    await ctx.send("Ranking multipoll results.", ephemeral=True)

    # Clear previous medal reactions if present.
    for poll_option in last_multipoll.poll_options:
        message = poll_option.message
        for reaction in message.reactions:
            if reaction.me and reaction.emoji.name in MEDALS:
                await message.remove_reaction(reaction.emoji)

    # Add updated medal reactions
    poll_options_by_score = last_multipoll.poll_options_by_score()
    rank = 1
    for score in sorted(poll_options_by_score.keys(), reverse=True):
        tied_poll_options = poll_options_by_score[score]

        medal_emoji = MEDALS[rank - 1]

        for poll_option in tied_poll_options:
            await poll_option.message.create_reaction(medal_emoji)

        rank += len(tied_poll_options)
        if rank > len(MEDALS):
            break


class MultipollResult:
    def __init__(self, poll_option: Message, ranking_mode: ResultRankingMode):
        self.name = poll_option.content
        self.message = poll_option
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
            if reaction.emoji.name == emoji:
                return reaction.count - 1  # This bot added all the reactions.
        return 0


class Multipoll:
    def __init__(self, question_message: Message, poll_option_messages: [Message],
                 ranking_mode: ResultRankingMode = ResultRankingMode.SCORE):
        self.question_message = question_message
        self.poll_options = list(map(lambda msg: MultipollResult(msg, ranking_mode), poll_option_messages))

    def question(self) -> str:
        if self.question_message is not None:
            return self.question_message.content[len(MULTIPOLL_QUESTION_PREFIX):]
        else:
            return "Unknown question?"

    def poll_options_by_score(self) -> {int: [MultipollResult]}:
        poll_options_by_score = {}

        for poll_option in self.poll_options:
            score = poll_option.score
            if score not in poll_options_by_score:
                poll_options_by_score[score] = []
            poll_options_by_score.get(score).append(poll_option)

        return poll_options_by_score


async def find_multipoll(ctx: SlashContext, ranking_mode: ResultRankingMode = ResultRankingMode.SCORE) \
        -> Optional[Multipoll]:
    poll_options = []
    found_multipoll = False
    question = None
    bot_user = User(**(await ctx.client.get_self()))
    for message in await ctx.channel.history(limit=200).flatten():
        if message.author != bot_user:
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
            elif any(reaction.me for reaction in (message.reactions or [])):
                # print("Found multipoll option: " + message.content)
                poll_options.append(message)

    # Verify the question was found.
    if not found_multipoll:
        await ctx.send("Could not find recent multipoll.", ephemeral=True)
        return None

    return Multipoll(question_message=question, poll_option_messages=poll_options, ranking_mode=ranking_mode)
