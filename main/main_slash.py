import os
import shlex
from datetime import datetime

import discord
from discord import Member, Message
from discord.ext import commands
from discord.ext import tasks
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from dotenv import load_dotenv

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
MULTIPOLL_HELP_MESSAGE =\
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
    # Send initial response
    await ctx.send(MULTIPOLL_QUESTION_PREFIX + question)

    option_list = shlex.split(options)

    # Send the rest of the poll messages. Send these directly to the channel so they don't have a bulky reply link.
    option_messages = []
    for option in option_list:
        option_messages.append(await ctx.channel.send(option))
    await ctx.channel.send(MULTIPOLL_HELP_MESSAGE)

    # Add emoji reactions
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
            if message.content == MULTIPOLL_HELP_MESSAGE:
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


'''
Example of how to read message history + reactions. Might be useful for poll counting?
@slash.slash(
    name="count_reactions",
    description="Count reactions on recent messages.",
    guild_ids=[834548590399586365], # Bot Testing
    options=[
        create_option(
            name="num_messages",
            description="Number of recent messages for which to count reactions",
            required=False,
            option_type=4,
        ),
    ],
)
async def count_reactions(ctx: SlashContext, num_messages: int = 1):
    await ctx.send(f"Counting emojis for last {num_messages} messages", hidden=True)
    async for message in ctx.channel.history(limit=min(num_messages, 50)):
        response = "Reaction counts of message - "
        for react in message.reactions:
            response += str(react.emoji) + ":" + str(react.count) + " "
        await ctx.channel.send(response, reference=message)
'''

# Loads the .env file that resides on the same level as the script.
load_dotenv()

# Grab the API token from the .env file. This file is NOT included in the git repository, as it contains credentials.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Executes the bot with the specified token.
bot.run(DISCORD_TOKEN)
