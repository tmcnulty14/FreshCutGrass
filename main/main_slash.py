import os
import shlex

from discord import Member
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from dotenv import load_dotenv

MULTIPOLL_EMOJIS = ["🍏", "🤨", "🥶", "🚫"]
GUILD_IDS = [834548590399586365, 933438152826306640, 771115921443651615]

bot = commands.Bot(command_prefix="!")
slash = SlashCommand(bot, sync_commands=True)


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
    await ctx.send("New poll: " + question)

    option_list = shlex.split(options)

    # Send the rest of the poll messages. Send these directly to the channel so they don't have a bulky reply link.
    option_messages = []
    for option in option_list:
        option_messages.append(await ctx.channel.send(option))
    await ctx.channel.send("Click one reaction on each poll option. 🍏 = Yes, 🤨 = Maybe, 🥶 = Likely Not, 🚫 = No")

    # Add emoji reactions
    for emoji in MULTIPOLL_EMOJIS:
        for message in option_messages:
            await message.add_reaction(emoji)


# Loads the .env file that resides on the same level as the script.
load_dotenv()

# Grab the API token from the .env file. This file is NOT included in the git repository, as it contains credentials.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Executes the bot with the specified token.
bot.run(DISCORD_TOKEN)
