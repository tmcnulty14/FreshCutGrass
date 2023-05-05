import os
from datetime import datetime
from dotenv import load_dotenv
from interactions import Activity, ActivityType, Client, Intents, IntervalTrigger, Member, OptionType, \
    SlashContext, Status, Task, listen, slash_command, slash_option
from pytz import timezone

# GUILD_IDS = [
#     834548590399586365,  # Bot Testing
#     933438152826306640,  # D&D: Wildemount
#     771115921443651615,  # Edmung Us
# ]

# Loads the .env file that resides on the same level as the script.
load_dotenv()

# Grab the API token from the .env file. This file is NOT included in the git repository, as it contains credentials.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Creates the bot with the specified token.
bot = Client(token=DISCORD_TOKEN, intents=Intents.DEFAULT)


@listen()
async def on_startup():
    # Print debug info about the guilds the bot is active in.
    print("FreshCutGrass is now active in " + str(len(bot.guilds)) + " guilds:")
    for guild in bot.guilds:
        print(f"- {guild.name} (id: {guild.id})")

    update_status.start()
    await update_status()


# @listen()
# async def on_message_create(message: MessageCreate):
#     # Lemon react to mentions of Myron Lermontov.
#     lemon_triggers = ["lermontov", "lairmontov"]
#
#     if any(trigger in message.message.content.lower() for trigger in lemon_triggers):
#         await message.message.add_reaction("🍋")  # Lemon emoji


@Task.create(IntervalTrigger(minutes=10))
async def update_status():
    now = datetime.now(timezone('US/Pacific'))
    status: Status
    activity: Activity
    if now.weekday() == 3 and now.hour >= 18:
        # It's Thursday Niiiiight
        print("Setting status to streaming twitch.tv/criticalrole")
        status = Status.ONLINE
        activity = Activity.create(name="Critical Role",
                                   type=ActivityType.STREAMING,
                                   url="https://www.twitch.tv/criticalrole")
    else:
        print("Setting status to playing Dungeons & Dragons")
        status = Status.ONLINE
        activity = Activity.create(name="Dungeons and Dragons",
                                   type=ActivityType.GAME)
    await bot.change_presence(status=status, activity=activity)


@slash_command(
    name="hello",
    description="Say hello",
    # Global command; allows this to be used in bot DMs.
    dm_permission=True,
)
@slash_option(
    name="member",
    description="Select a user",
    required=False,
    opt_type=OptionType.USER,
)
async def hello(ctx: SlashContext, member: Member = None):
    user = ctx.author
    if member is not None:
        user = member.user

    await ctx.send("Smiley day to you, " + user.mention + "!")


bot.load_extension("polls")
bot.load_extension("wikidot_scraper")

# Run the bot.
bot.start()
