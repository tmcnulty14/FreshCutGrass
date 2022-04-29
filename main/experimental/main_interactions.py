import os
from shlex import split

import interactions
from dotenv import load_dotenv

default_multipoll_emojis = ["🍏", "🤨", "🥶", "🚫"]

# Loads the .env file that resides on the same level as the script.
load_dotenv()

# Grab the API token from the .env file.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
bot = interactions.Client(token=DISCORD_TOKEN)


@bot.command(
    name="hello",
    description="Say hello to someone",
    options=[
        interactions.Option(
            name="person",
            description="The person to greet",
            type=interactions.OptionType.USER,
            required=False,
        ),
    ],
)
async def hello(ctx: interactions.CommandContext, person: interactions.Member = None):
    to_greet = person or ctx.author.user

    print("Greeting" + to_greet.username)

    await ctx.send("Smiley day to ya, " + to_greet.mention + "!")


@bot.command(
    name="multipoll",
    description="Create a poll with multiple options.",
    options=[
        interactions.Option(
            name="options_str",
            description="The poll options, e.g.: A B \"The letter C\"",
            type=interactions.OptionType.STRING,
            required=True,
        )
    ],
)
async def multipoll(ctx: interactions.CommandContext, options_str: str):
    options = split(options_str)
    for option in options:
        message = await ctx.send(option)

        for emoji in default_multipoll_emojis:
            await message.add_reaction(emoji)  # TODO Doesn't exist in interactions API?


# Run the bot.
bot.start()
