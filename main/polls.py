import shlex

import discord
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
    poll_question = MULTIPOLL_QUESTION_PREFIX + question
    poll_options = shlex.split(options)

    # Send question message, options messages, and help text message
    sent_messages = await utils.send_multiple_replies(ctx, [poll_question] + poll_options + [MULTIPOLL_HELP_TEXT])

    # Add emoji reactions
    option_messages = sent_messages[1:-1]
    for emoji in MULTIPOLL_EMOJIS:
        for message in option_messages:
            await message.add_reaction(emoji)


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

    poll_options_by_score = {}
    for poll_option in poll_options:
        score = poll_option.score
        if not score in poll_options_by_score:
            poll_options_by_score[score] = []
        poll_options_by_score.get(score).append(poll_option)

    embed = discord.Embed(
        title="Poll Results",
        description=question.content[len(MULTIPOLL_QUESTION_PREFIX):],
        color=discord.Color.gold(),
    )
    rank = 1
    for score in sorted(poll_options_by_score.keys(), reverse=True):
        tied_poll_options = sorted(poll_options_by_score[score], key=lambda p: p.name)
        for poll_option in tied_poll_options:
            embed.add_field(name="\n" + str(rank) + ". " + poll_option.name, value="> " + poll_option.emoji_str(),
                            inline=False)
        rank += len(tied_poll_options)

    await ctx.channel.send(embed=embed, reference=question)


class MultipollResult:
    def __init__(self, poll_option: Message):
        self.name = poll_option.content

        self.yes = count_reaction(poll_option, YES)
        self.maybe = count_reaction(poll_option, MAYBE)
        self.unlikely = count_reaction(poll_option, UNLIKELY)
        self.no = count_reaction(poll_option, NO)

        self.score = 3 * self.yes + self.maybe + -1 * self.unlikely + -3 * self.no

    def __str__(self):
        return self.name + f" [Score: {self.score}] " + self.emoji_str()

    def __lt__(self, other):
        return self.score.__lt__(other.score)

    def emoji_str(self):
        return YES * self.yes + MAYBE * self.maybe + UNLIKELY * self.unlikely + NO * self.no


def count_reaction(message: Message, emoji: str):
    for reaction in message.reactions:
        if reaction.emoji == emoji:
            return reaction.count - 1  # This bot added all the reactions.
    return 0
