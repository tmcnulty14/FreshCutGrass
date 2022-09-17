import re
import urllib.request
from html.parser import HTMLParser
from os import linesep
from typing import Optional
from urllib.error import HTTPError

from interactions.api.models.message import Embed
from interactions.api.models.misc import Color

import utils

WIKIDOT_URL_PREFIX = "http://dnd5e.wikidot.com/"
DIVS_TO_PARSE = ['page-title page-header', 'page-content']


def get_dnd_spell_text(spell_name: str) -> str:
    wikidot_path = get_wikidot_path("spell", spell_name)

    try:
        return get_wikidot_page_text(wikidot_path)
    except HTTPError:
        return f"Error: Could not find a DnD 5e spell named **{spell_name}**."


def get_wikidot_text(category: str, name: str) -> str:
    wikidot_path = get_wikidot_path(category, name)

    try:
        return get_wikidot_page_text(wikidot_path)
    except HTTPError:
        return f"Error: Could not find **{name}** in category **{category}**."


def get_wikidot_path(category: str, name: str) -> str:
    return wikidot_url_format(category) + ":" + wikidot_url_format(name)


def wikidot_url_format(url_component: str) -> str:
    formatted_url_component = url_component.lower()
    formatted_url_component = re.sub("[/ ]+", '-', formatted_url_component)
    return re.sub("[^A-Za-z-]+", '', formatted_url_component)


def get_wikidot_page_text(page_path: str) -> str:
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
                self.output += '__ '
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


class DndWikidotCard:
    # This is the Braille 'blank' character. It's a hacky way to satisfy the requirement that Field titles aren't empty.
    EMPTY_FIELD_TITLE_CHARACTER = '⠀'

    def __init__(self, lines: [str]):
        self.lines = lines

    def find_line(self, line_prefix: str) -> Optional[str]:
        return next(l for l in self.lines if l.startswith(line_prefix))

    def get_lines_between(self, previous_line_exclusive: str, next_line_exclusive):
        previous_line_index = self.lines.index(previous_line_exclusive)
        next_line_index = self.lines.index(next_line_exclusive)

        return self.lines[previous_line_index + 1:next_line_index]

    def get_lines_after(self, previous_line_exclusive: str):
        previous_line_index = self.lines.index(previous_line_exclusive)

        return self.lines[previous_line_index+1:]

    @staticmethod
    def group_lines_by_max_character_count(lines: [str]) -> [str]:
        blob = linesep.join(lines)
        split_groups = list(utils.smart_split(blob, 1024))
        return split_groups

    @staticmethod
    def add_long_text_as_multiple_fields(card: Embed, field_name: str, text_lines: [str]):
        text_groups = DndWikidotCard.group_lines_by_max_character_count(text_lines)
        card.add_field(name=field_name, value=text_groups[0], inline=False)
        for text_group in text_groups[1:]:
            card.add_field(name=DndSpell.EMPTY_FIELD_TITLE_CHARACTER, value=text_group, inline=False)


class DndSpell(DndWikidotCard):
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
        spell_text = get_wikidot_text("Spell", spell_name)
        self.lines = spell_text.split(linesep)
        DndWikidotCard.__init__(self, lines=self.lines)

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

    def get_school_image_url(self):
        school = next(school for school in DndSpell.SCHOOL_TO_IMAGE_MAP.keys() if school in self.classification.lower())
        return DndSpell.SCHOOL_TO_IMAGE_MAP[school]

    def make_card(self) -> Embed:
        card = Embed(
            title=self.name,
            description=self.classification,
            color=Color.yellow()
        )

        # Casting details
        card.add_field(name="Casting Time", value=self.cast_time[18:], inline=True)
        card.add_field(name="Range", value=self.range[11:], inline=True)
        card.add_field(name="Duration", value=self.duration[14:], inline=True)
        card.add_field(name="Components", value=self.components[16:], inline=True)

        self.add_long_text_as_multiple_fields(card, "Description", self.description_lines)

        card.add_field(name="Spell Lists", value=self.spell_lists[19:], inline=False)

        if len(self.extra_lines) > 1:
            self.add_long_text_as_multiple_fields(card, self.extra_lines[0], self.extra_lines[1:])

        card.set_footer(text=self.source, icon_url=self.get_school_image_url())

        return card


def get_dnd_spell_card(spell_name: str) -> Embed:
    return DndSpell(spell_name).make_card()


class DndItem(DndWikidotCard):
    # Get Magic Item Type image URLs from DnDBeyond.
    ITEM_TYPE_TO_IMAGE_MAP = {
        'armor': 'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/armor.jpg',
        'potion': 'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/potion.jpg',
        'ring': 'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/ring.jpg',
        'rod': 'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/rod.jpg',
        'scroll': 'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/scroll.jpg',
        'staff': 'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/staff.jpg',
        'wand': 'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/wand.jpg',
        'weapon': 'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/weapon.jpg',
        'wondrous item':
            'https://www.dndbeyond.com/content/1-0-1989-0/skins/waterdeep/images/icons/item_types/wondrousitem.jpg',
    }

    def __init__(self, item_name: str):
        item_text = get_wikidot_text("Wondrous Items", item_name)
        self.lines = item_text.split(linesep)
        DndWikidotCard.__init__(self, lines=self.lines)

        self.name = self.lines[0]
        self.source = self.find_line("Source: ")

        further_lines = self.get_lines_after(self.source)
        self.metadata_line = further_lines[1]
        self.description_lines = further_lines[2:]

        self.item_type, remaining_metadata = self.metadata_line.strip('*').split(',', 1)
        if '(requires attunement' in remaining_metadata:
            attunement_start = remaining_metadata.index('(requires attunement')
            self.rarity = remaining_metadata[:attunement_start - 1]
            self.attunement = remaining_metadata[attunement_start + 1:].split(')', 1)[0]
        else:
            self.rarity = remaining_metadata
            self.attunement = None

    def get_item_type_image_url(self):
        return DndItem.ITEM_TYPE_TO_IMAGE_MAP[self.item_type.lower()]

    def make_card(self) -> Embed:
        card = Embed(
            title=self.name,
            color=Color.yellow(),
        )

        card.add_field(name="Item Type", value=self.item_type, inline=True)
        card.add_field(name="Rarity", value=self.rarity, inline=True)
        if self.attunement:
            card.add_field(name="Attunement", value=self.attunement, inline=True)

        self.add_long_text_as_multiple_fields(card, "Description", self.description_lines)

        card.set_footer(text=self.source, icon_url=self.get_item_type_image_url())

        return card


def get_dnd_item_card(item_name: str) -> Embed:
    return DndItem(item_name).make_card()