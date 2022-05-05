import re
import urllib.request
from html.parser import HTMLParser
from os import linesep
from typing import Optional
from urllib.error import HTTPError

import discord
from discord import Embed

import utils

WIKIDOT_URL_PREFIX = "http://dnd5e.wikidot.com/"
DIVS_TO_PARSE = ['page-title page-header', 'page-content']


def get_dnd_spell_text(spell_name: str) -> str:
    wikidot_path = get_wikidot_path(spell_name)

    try:
        return get_wikidot_text(wikidot_path)
    except HTTPError:
        return f"Error: Could not find a DnD 5e spell named **{spell_name}**."


def get_wikidot_url(spell_name: str) -> str:
    return WIKIDOT_URL_PREFIX + get_wikidot_path(spell_name)


def get_wikidot_path(spell_name: str) -> str:
    formatted_spell_name = spell_name.lower()
    formatted_spell_name = re.sub("[/ ]+", '-', formatted_spell_name)
    formatted_spell_name = re.sub("[^A-Za-z-]+", '', formatted_spell_name)
    return "spell:" + formatted_spell_name

def get_wikidot_text(page_path: str) -> str:
    html = get_wikidot_html(page_path)
    return parse_wikidot_html(html)


def get_wikidot_html(page_path: str) -> bytes:
    url = WIKIDOT_URL_PREFIX + page_path
    print(f"Looking up Wikidot URL: {url}")

    page = urllib.request.urlopen(url)
    return page.read()


def parse_wikidot_html(html_content: bytes) -> str:
    return WikidotHtmlParser().feed(html_content.decode('utf-8'))


class WikidotHtmlParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

        # Initialize parsing fields
        self.output = ""
        self.current_parsing_div_level = -1
        self.div_level = 0

    def is_parsing_content_div(self):
        return self.current_parsing_div_level != -1

    def feed(self, data):
        # Reset parsing fields
        self.output = ""
        self.current_parsing_div_level = -1
        self.div_level = 0

        super(WikidotHtmlParser, self).feed(data)

        return self.output

    def handle_data(self, data: str):
        # Only parse data within the main-content div.
        if self.is_parsing_content_div():  # and 'nitroAds' not in data:
            self.output += data.strip()

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            for (attribute_key, attribute_value) in attrs:
                if attribute_key == 'class' or attribute_key == 'id':
                    if attribute_value in DIVS_TO_PARSE and not self.is_parsing_content_div():
                        self.current_parsing_div_level = self.div_level

            self.div_level += 1

        if self.is_parsing_content_div():
            if tag == 'strong':
                self.output += '**'
            if tag == 'em':
                self.output += '*'
            if tag == 'br':
                self.output += linesep
            if tag == 'p':
                self.output += linesep
            if tag == 'span':
                self.output += '__**'
            if tag == 'th':
                self.output += '__'
            if tag == 'li':
                self.output += '• '
            if tag == 'a':
                self.output += ' '
            return

    def handle_endtag(self, tag):
        if tag == 'div':
            self.div_level -= 1

            # Check if this closes any tracked divs.
            if self.div_level == self.current_parsing_div_level:
                self.current_parsing_div_level = -1
        elif self.is_parsing_content_div():
            if tag == 'strong':
                self.output += '** '
            if tag == 'em':
                self.output += '* '
            if tag == 'p':
                self.output += linesep
            if tag == 'span':
                self.output += '**__'
            if tag == 'tr':
                self.output += linesep
            if tag == 'th':
                self.output += '__\t\t\t'
            if tag == 'td':
                self.output += '\t\t\t'
            if tag == 'li':
                self.output += linesep
            return

    def error(self, message):
        print(f"Parsing error: {message}")

class DndSpell:
    # This is the Braille 'blank' character. It's a hacky way to satisfy the requirement that Field titles aren't empty.
    EMPTY_FIELD_TITLE_CHARACTER = '⠀'
    # Get School of Magic image URLs from DnDBeyond.
    SCHOOL_TO_IMAGE_MAP = {
        'abjuration': 'https://media-waterdeep.cursecdn.com/attachments/2/707/abjuration.png',
        'conjuration': 'https://media-waterdeep.cursecdn.com/attachments/2/708/conjuration.png',
        'divination': 'https://media-waterdeep.cursecdn.com/attachments/2/709/divination.png',
        'enchantment': 'https://media-waterdeep.cursecdn.com/attachments/2/702/enchantment.png',
        'evocation': 'https://media-waterdeep.cursecdn.com/attachments/2/703/evocation.png',
        'illusion': 'https://media-waterdeep.cursecdn.com/attachments/2/704/illusion.png',
        'necromancy': 'https://media-waterdeep.cursecdn.com/attachments/2/720/necromancy.png',
        'transmutation': 'https://media-waterdeep.cursecdn.com/attachments/2/722/transmutation.png',
    }

    def __init__(self, spell_name: str):
        self.spell_name = spell_name
        spell_text = get_dnd_spell_text(spell_name)
        self.lines = spell_text.split(linesep)

        self.name = self.lines[0]
        self.source = self.find_line("Source: ")
        self.cast_time = self.find_line("**Casting Time:")
        self.range = self.find_line("**Range:** ")
        self.components = self.find_line("**Components:")
        self.duration = self.find_line("**Duration:")
        self.spell_lists = self.find_line("***Spell Lists.")

        self.classification = self.get_lines_between(self.source, self.cast_time)[1]
        self.description_lines = self.get_lines_between(self.duration, self.spell_lists)[1:-1]
        self.extra_lines = self.get_lines_after(self.spell_lists)

    def find_line(self, line_prefix: str) -> Optional[str]:
        return next(l for l in self.lines if l.startswith(line_prefix))

    def get_lines_between(self, previous_line_exclusive: str, next_line_exclusive):
        previous_line_index = self.lines.index(previous_line_exclusive)
        next_line_index = self.lines.index(next_line_exclusive)

        return self.lines[previous_line_index + 1:next_line_index]

    def get_lines_after(self, previous_line_exclusive: str):
        previous_line_index = self.lines.index(previous_line_exclusive)

        return self.lines[previous_line_index+1:]

    def get_school_image_url(self):
        school = next(school for school in DndSpell.SCHOOL_TO_IMAGE_MAP.keys() if school in self.classification.lower())
        return DndSpell.SCHOOL_TO_IMAGE_MAP[school]

    def make_card(self) -> Embed:
        card = Embed(
            title=self.name,
            description=self.classification,
            color=discord.Color.gold(),
        )

        # Casting details
        card.add_field(name="Casting Time", value=self.cast_time[18:], inline=True)
        card.add_field(name="Range", value=self.range[11:], inline=True)
        card.add_field(name="Duration", value=self.duration[14:], inline=True)
        card.add_field(name="Components", value=self.components[16:], inline=True)

        description_groups = self.group_lines_by_max_character_count(self.description_lines)
        card.add_field(name="Description", value=description_groups[0], inline=False)
        for description_group in description_groups[1:]:
            card.add_field(name=DndSpell.EMPTY_FIELD_TITLE_CHARACTER, value=description_group, inline=False)

        card.add_field(name="Spell Lists", value=self.spell_lists[19:], inline=False)

        if len(self.extra_lines) > 1:
            extra_groups = self.group_lines_by_max_character_count(self.extra_lines[1:])
            card.add_field(name=self.extra_lines[0], value=extra_groups[0], inline=False)
            for extra_group in extra_groups[1:]:
                card.add_field(name=DndSpell.EMPTY_FIELD_TITLE_CHARACTER, value=extra_group, inline=False)

        card.set_footer(text=self.source, icon_url=self.get_school_image_url())

        return card

    @staticmethod
    def group_lines_by_max_character_count(lines: [str]) -> [str]:
        blob = linesep.join(lines)
        split_groups = list(utils.smart_split(blob, 1024))
        return split_groups


def get_dnd_spell_card(spell_name: str) -> Embed:
    return DndSpell(spell_name).make_card()