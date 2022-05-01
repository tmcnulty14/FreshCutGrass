import os
import shlex
from datetime import datetime
from os import linesep
from typing import Iterator, Iterable

import discord
from discord import Member, Message
from discord.ext import commands
from discord.ext import tasks
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from dotenv import load_dotenv
from interactions import OptionType

from wikidot.scraper import get_dnd_spell_text

GUILD_IDS = [
    834548590399586365, # Bot Testing
    933438152826306640, # D&D: Wildemount
    771115921443651615, # Edmung Us
]
YES = "🍏"
MAYBE = "🤨"
UNLIKELY = "🥶"
NO = "🚫"
MULTIPOLL_EMOJIS = [YES, MAYBE, UNLIKELY, NO]
MULTIPOLL_QUESTION_PREFIX = "New poll: "
MULTIPOLL_HELP_TEXT =\
    f"Click one reaction on each poll option. {YES} = Yes, {MAYBE} = Maybe, {UNLIKELY} = Likely Not, {NO} = No"

bot = commands.Bot(command_prefix="!")
slash = SlashCommand(bot, sync_commands=True)


@bot.event
async def on_ready():
    # Print debug info about the guilds the bot is active in.
    print("FreshCutGrass is now active in " + str(len(bot.guilds)) + " guilds:")
    for guild in bot.guilds:
        print(f"- {guild.name} (id: {guild.id})")

    await update_status()


@bot.event
async def on_message(message: Message):
    # Lemon react to mentions of Myron Lermontov.
    lemon_triggers = ["lermontov", "lairmontov"]
    if any(trigger in message.content.lower() for trigger in lemon_triggers):
        await message.add_reaction("🍋") # Lemon emoji


@tasks.loop(hours=1)
async def update_status():
    now = datetime.now()
    if (now.weekday() == 3 and now.hour >= 21) or (now.weekday() == 4 and now.hour <= 2):
        # It's Thursday Niiiiight
        print("Setting status to streaming twitch.tv/criticalrole")
        await bot.change_presence(activity=discord.Streaming(name="Critical Role",
                                                             url="https://www.twitch.tv/criticalrole"))
    else:
        print("Setting status to playing Dungeons & Dragons")
        await bot.change_presence(activity=discord.Game("Dungeons and Dragons"))


@slash.slash(
    name="hello",
    description="Say hello",
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="member",
            description="Select a user",
            required=False,
            option_type=6,
        ),
    ],
)
async def hello(ctx: SlashContext, member: Member = None):
    user = ctx.author
    if member is not None:
        user = member._user

    await ctx.send("Smiley day to you, " + user.mention + "!")


@slash.slash(
    name="multipoll",
    description="Create a poll with multiple options.",
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="question",
            description="The poll question.",
            required=True,
            option_type=3,
        ),
        create_option(
            name="options",
            description="The poll options, separated by spaces. Wrap with quotes to include a space in an option.",
            required=True,
            option_type=3,
        ),
    ],
)
async def multipoll(ctx: SlashContext, question: str, options: str):
    poll_question = MULTIPOLL_QUESTION_PREFIX + question
    poll_options = shlex.split(options)

    # Send question message, options messages, and help text message
    sent_messages = await send_multiple_replies(ctx, [poll_question] + poll_options + [MULTIPOLL_HELP_TEXT])

    # Add emoji reactions
    option_messages = sent_messages[1:-1]
    for emoji in MULTIPOLL_EMOJIS:
        for message in option_messages:
            await message.add_reaction(emoji)


@slash.slash(
    name="multipoll_results",
    description="Ranks the results of the last multipoll.",
    guild_ids=GUILD_IDS,
)
async def multipoll_results(ctx: SlashContext):
    await ctx.send("Fetching multipoll results...", hidden=True)

    poll_options = []
    found_multipoll = False
    question: Message
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
                poll_options.append(MultipollResult(message))

    # Verify the question was found.
    if not question:
        await ctx.channel.send("Could not find recent multipoll.", delete_after=5)
        return

    sorted_poll_options = sorted(poll_options, reverse=True)

    summary = "Results for: **" + question.content[len(MULTIPOLL_QUESTION_PREFIX):] + "**"
    rank = 1
    for poll_option in sorted_poll_options:
        summary += "\n" + str(rank) + ". " + str(poll_option)
        rank += 1
    await ctx.channel.send(summary, reference=question)


class MultipollResult:
    def __init__(self, poll_option: Message):
        self.name = poll_option.content

        self.yes = count_reaction(poll_option, YES)
        self.maybe = count_reaction(poll_option, MAYBE)
        self.unlikely = count_reaction(poll_option, UNLIKELY)
        self.no = count_reaction(poll_option, NO)

        self.score = 3 * self.yes + self.maybe + -1 * self.unlikely + -3 * self.no

    def __str__(self):
        return self.name + f" [Score: {self.score}] "\
               + YES * self.yes + MAYBE * self.maybe + UNLIKELY * self.unlikely + NO * self.no

    def __lt__(self, other):
        return self.score.__lt__(other.score)


def count_reaction(message: Message, emoji: str):
    for reaction in message.reactions:
        if reaction.emoji == emoji:
            return reaction.count - 1  # This bot added all the reactions.
    return 0


@slash.slash(
    name="spell_lookup",
    description="Look up a DnD 5e spell",
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="spell_name",
            description="The spell name",
            required=True,
            option_type=OptionType.STRING,
        ),
    ],
)
async def spell_lookup(ctx: SlashContext, spell_name: str):
    text: str = get_dnd_spell_text(spell_name)

    # Some spells are longer than Discord message limit; split these into multiple messages.
    messages = list(smart_split(text, 2000))

    await send_multiple_replies(ctx, messages, delete_after=600)
    # await ctx.send(next(messages), delete_after=600)
    # for message in messages:
    #     await ctx.channel.send(message, delete_after=600)


def smart_split(string: str, length_limit: int) -> Iterator[str]:
    """
    A utility method that splits a string up into substrings no longer than the given limit, but tries to split the
    strings around line breaks.
    :param string: The string to split.
    :param length_limit: The length limit of substrings.
    :return: A generator of the split substrings.
    """
    remaining_string = string
    while remaining_string != '':
        substring = remaining_string[:length_limit]
        remaining_string = remaining_string[length_limit:]

        (final_substring, extra_remainder) = substring.rsplit(linesep, 1)
        yield final_substring
        remaining_string = extra_remainder + remaining_string


async def send_multiple_replies(ctx: SlashContext, messages: Iterable[str], delete_after: float = None) -> [Message]:
    iterator: Iterator[str] = iter(messages)

    # Send first message as a direct reply to the slash command.
    sent_messages = [await ctx.send(next(iterator), delete_after=delete_after)]

    # Send any further messages directly to the channel so the whole response is compactly spaced.
    for message in iterator:
        sent_messages.append(await ctx.channel.send(message, delete_after=delete_after))

    return sent_messages


# Loads the .env file that resides on the same level as the script.
load_dotenv()

# Grab the API token from the .env file. This file is NOT included in the git repository, as it contains credentials.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Executes the bot with the specified token.
bot.run(DISCORD_TOKEN)
