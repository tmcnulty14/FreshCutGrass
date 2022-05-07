import os
from datetime import datetime

import discord
from discord import Member, Message
from discord.ext import commands
from discord.ext import tasks
from discord_slash import SlashCommand, SlashContext, SlashCommandOptionType
from discord_slash.utils.manage_commands import create_choice, create_option
from dotenv import load_dotenv

import polls
from wikidot_scraper import get_dnd_spell_card, get_dnd_item_card

GUILD_IDS = [
    834548590399586365, # Bot Testing
    933438152826306640, # D&D: Wildemount
    771115921443651615, # Edmung Us
]

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
    # Global command; allows this to be used in bot DMs.
    options=[
        create_option(
            name="member",
            description="Select a user",
            required=False,
            option_type=SlashCommandOptionType.USER,
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
            option_type=SlashCommandOptionType.STRING,
        ),
        create_option(
            name="options",
            description="The poll options, separated by spaces. Wrap with quotes to include a space in an option.",
            required=True,
            option_type=SlashCommandOptionType.STRING,
        ),
    ],
)
async def multipoll(ctx: SlashContext, question: str, options: str):
    await polls.multipoll(ctx, question, options)


@slash.slash(
    name="schedule",
    description="Create a scheduling poll.",
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="question",
            description="The poll question.",
            required=True,
            option_type=SlashCommandOptionType.STRING,
        ),
        create_option(
            name="start_date",
            description="The start date of the scheduling range. Defaults to tomorrow.",
            required=False,
            option_type=SlashCommandOptionType.STRING,
        ),
        create_option(
            name="end_date",
            description="The end date of the scheduling range. Defaults to one week after the start date.",
            required=False,
            option_type=SlashCommandOptionType.STRING,
        ),
    ],
)
async def schedule(ctx: SlashContext, question: str, start_date: str = None, end_date: str = None):
    await polls.scheduling_multipoll(ctx, question, start_date, end_date)


@slash.slash(
    name="multipoll_results",
    description="Ranks the results of the last multipoll.",
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="ranking_mode",
            description="The mode to use for ranking results",
            option_type=SlashCommandOptionType.STRING,
            required=False,
            choices=list(map(lambda ranking_mode_name: create_choice(name=ranking_mode_name, value=ranking_mode_name),
                             polls.ResultRankingMode.__members__.keys())),
        ),
    ],
)
async def multipoll_results(ctx: SlashContext, ranking_mode: str = polls.ResultRankingMode.SCORE.name):
    await polls.multipoll_results(ctx, ranking_mode)


@slash.slash(
    name="spell_lookup",
    description="Look up a DnD 5e spell",
    # Global command; allows this to be used in bot DMs.
    options=[
        create_option(
            name="spell_name",
            description="The spell name",
            required=True,
            option_type=SlashCommandOptionType.STRING,
        ),
    ],
)
async def spell_lookup(ctx: SlashContext, spell_name: str):
    card: discord.Embed = get_dnd_spell_card(spell_name)

    await ctx.send(embed=card, delete_after=600)


@slash.slash(
    name="item_lookup",
    description="Look up a DnD 5e magic item",
    # Global command; allows this to be used in bot DMs.
    options=[
        create_option(
            name="item_name",
            description="The item name",
            required=True,
            option_type=SlashCommandOptionType.STRING,
        ),
    ],
)
async def item_lookup(ctx: SlashContext, item_name: str):
    card: discord.Embed = get_dnd_item_card(item_name)

    await ctx.send(embed=card, delete_after=600)


# Loads the .env file that resides on the same level as the script.
load_dotenv()

# Grab the API token from the .env file. This file is NOT included in the git repository, as it contains credentials.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Executes the bot with the specified token.
bot.run(DISCORD_TOKEN)
