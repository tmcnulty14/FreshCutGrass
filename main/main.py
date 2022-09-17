import os
from datetime import datetime

from discord.ext import tasks
from dotenv import load_dotenv
from interactions import ClientPresence, OptionType, CommandContext, Option, Choice, Client, StatusType, \
    PresenceActivity, PresenceActivityType, Message, Member, Role
from interactions.api.models.message import Embed

import polls
from wikidot_scraper import get_dnd_spell_card, get_dnd_item_card

GUILD_IDS = [
    # 834548590399586365,  # Bot Testing
    933438152826306640,  # D&D: Wildemount
    771115921443651615,  # Edmung Us
]

# Loads the .env file that resides on the same level as the script.
load_dotenv()

# Grab the API token from the .env file. This file is NOT included in the git repository, as it contains credentials.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Creates the bot with the specified token.
bot = Client(token=DISCORD_TOKEN)


@bot.event
async def on_ready():
    # Print debug info about the guilds the bot is active in.
    print("FreshCutGrass is now active in " + str(len(bot.guilds)) + " guilds:")
    for guild in bot.guilds:
        print(f"- {guild.name} (id: {guild.id})")

    # await update_status()  # TODO: Figure out why this is broken


@bot.event
async def on_message_create(message: Message):
    # Lemon react to mentions of Myron Lermontov.
    lemon_triggers = ["lermontov", "lairmontov"]
    if any(trigger in message.content.lower() for trigger in lemon_triggers):
        await message.create_reaction("🍋")  # Lemon emoji


# noinspection PyUnresolvedReferences
# @tasks.loop(hours=1)  # TODO: Figure out why this is broken
async def update_status():
    now = datetime.now()
    presence: ClientPresence
    if (now.weekday() == 3 and now.hour >= 21) or (now.weekday() == 4 and now.hour <= 2):
        # It's Thursday Niiiiight
        print("Setting status to streaming twitch.tv/criticalrole")
        presence = ClientPresence(
            status=StatusType.ONLINE,
            activities=[PresenceActivity(
                name="Critical Role",
                type=PresenceActivityType.STREAMING,
                url="https://www.twitch.tv/criticalrole"
            )]
        )
    else:
        print("Setting status to playing Dungeons & Dragons")
        presence = ClientPresence(
            status=StatusType.ONLINE,
            activities=[PresenceActivity(
                    name="Dungeons and Dragons",
                    type=PresenceActivityType.GAME
                )]
        )
    await bot.change_presence(presence=presence)


@bot.command(
    name="hello",
    description="Say hello",
    # Global command; allows this to be used in bot DMs.
    dm_permission=True,
    options=[
        Option(
            name="member",
            description="Select a user",
            required=False,
            type=OptionType.USER,
        ),
    ],
)
async def hello(ctx: CommandContext, member: Member = None):
    user = ctx.author
    if member is not None:
        user = member.user

    await ctx.send("Smiley day to you, " + user.mention + "!")


@bot.command(
    name="multipoll",
    description="Create a poll with multiple options.",
    scope=GUILD_IDS,
    options=[
        Option(
            name="question",
            description="The poll question.",
            required=True,
            type=OptionType.STRING,
        ),
        Option(
            name="options",
            description="The poll options, separated by spaces. Wrap with quotes to include a space in an option.",
            required=True,
            type=OptionType.STRING,
        ),
        Option(
            name="mention_role",
            description="A role to mention.",
            required=False,
            type=OptionType.ROLE,
        ),
    ],
)
async def multipoll(ctx: CommandContext, question: str, options: str, mention_role: Role = None):
    await polls.multipoll(ctx, question, options, mention_role)


@bot.command(
    name="schedule",
    description="Create a scheduling poll.",
    scope=GUILD_IDS,
    options=[
        Option(
            name="question",
            description="The poll question.",
            required=True,
            type=OptionType.STRING,
        ),
        Option(
            name="start_date",
            description="The start date of the scheduling range. Defaults to tomorrow.",
            required=False,
            type=OptionType.STRING,
        ),
        Option(
            name="end_date",
            description="The end date of the scheduling range. Defaults to one week after the start date.",
            required=False,
            type=OptionType.STRING,
        ),
        Option(
            name="mention_role",
            description="A role to mention.",
            required=False,
            type=OptionType.ROLE,
        ),
    ],
)
async def schedule(ctx: CommandContext, question: str, start_date: str = None, end_date: str = None,
                   mention_role: Role = None):
    await polls.scheduling_multipoll(ctx, question, start_date, end_date, mention_role)


@bot.command(
    name="multipoll_results",
    description="Ranks the results of the last multipoll.",
    scope=GUILD_IDS,
    options=[
        Option(
            name="ranking_mode",
            description="The mode to use for ranking results",
            type=OptionType.STRING,
            required=False,
            choices=list(map(lambda ranking_mode_name: Choice(name=ranking_mode_name, value=ranking_mode_name),
                             polls.ResultRankingMode.__members__.keys())),
        ),
    ],
)
async def multipoll_results(ctx: CommandContext, ranking_mode: str = polls.ResultRankingMode.SCORE.name):
    await polls.multipoll_results(ctx, ranking_mode)


@bot.command(
    name="spell_lookup",
    description="Look up a DnD 5e spell",
    # Global command; allows this to be used in bot DMs.
    options=[
        Option(
            name="spell_name",
            description="The spell name",
            required=True,
            type=OptionType.STRING,
        ),
    ],
)
async def spell_lookup(ctx: CommandContext, spell_name: str):
    card: Embed = get_dnd_spell_card(spell_name)

    await ctx.send(embeds=card)


@bot.command(
    name="item_lookup",
    description="Look up a DnD 5e magic item",
    # Global command; allows this to be used in bot DMs.
    options=[
        Option(
            name="item_name",
            description="The item name",
            required=True,
            type=OptionType.STRING,
        ),
    ],
)
async def item_lookup(ctx: CommandContext, item_name: str):
    card: Embed = get_dnd_item_card(item_name)

    await ctx.send(embeds=card)

# Run the bot.
bot.start()
