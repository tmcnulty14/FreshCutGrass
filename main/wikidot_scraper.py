import re
import urllib.request
from html.parser import HTMLParser
from os import linesep
from urllib.error import HTTPError

WIKIDOT_URL_PREFIX = "http://dnd5e.wikidot.com/"
DIVS_TO_PARSE = ['page-title page-header', 'page-content']


def get_dnd_spell_text(spell_name: str) -> str:
    formatted_spell_name = spell_name.lower()
    formatted_spell_name = re.sub("[/ ]+", '-', formatted_spell_name)
    formatted_spell_name = re.sub("[^A-Za-z-]+", '', formatted_spell_name)
    wikidot_path = "spell:" + formatted_spell_name

    try:
        return get_wikidot_text(wikidot_path)
    except HTTPError:
        return f"Error: Could not find a DnD 5e spell named **{spell_name}**."


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
            # print(f"Parsed data: {data}")
            self.output += data.strip()

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            for (attribute_key, attribute_value) in attrs:
                if attribute_key == 'class' or attribute_key == 'id':
                    if attribute_value in DIVS_TO_PARSE and not self.is_parsing_content_div():
                        self.current_parsing_div_level = self.div_level
                        # print(f"Entering content div {attribute_value}")

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
            return

    def handle_endtag(self, tag):
        if tag == 'div':
            self.div_level -= 1

            # Check if this closes any tracked divs.
            if self.div_level == self.current_parsing_div_level:
                self.current_parsing_div_level = -1
                # print("Exiting content div")
        elif self.is_parsing_content_div():
            if tag == 'strong':
                self.output += '** '
            if tag == 'em':
                self.output += '*'
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
            return

    def error(self, message):
        print(f"Parsing error: {message}")
