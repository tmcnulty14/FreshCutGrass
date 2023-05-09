import os.path
import string
from datetime import datetime, timedelta
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from interactions import Extension, Task, TimeTrigger, Embed, BrandColors, Timestamp, TimestampStyles, slash_command, \
    Button, PartialEmoji, ButtonStyle, listen, TYPE_ALL_CHANNEL, Message, SlashContext
from interactions.api.events import Component

from utils import find_matching_bot_message

# Google API scope
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

EVENT_GUILD_CHANNEL_CONFIG = {
    # Edmung Us server
    "771115921443651615": {
        # droop-troop channel
        "803481288870461500": {
            "title_prefix": "D&D TC",
            "event_image": "https://images.ctfassets.net/swt2dsco9mfe/48Nfrlty0IQe0NdGu3IvIq"
                           "/30fa851afad405a68fa247b13ea55b87/1920x1342-skt.jpg?q=70",
            "mention_role": "805283535186296892",  # DROOP TROOP
            "event_footer": "Storm King's Thunder session"
        }
    },
    # # Bot Testing server
    # "834548590399586365": {
    #     # general channel
    #     "834548590940520491": {
    #         "title_prefix": "D&D TC",
    #         "event_image": "https://images.ctfassets.net/swt2dsco9mfe/48Nfrlty0IQe0NdGu3IvIq"
    #                        "/30fa851afad405a68fa247b13ea55b87/1920x1342-skt.jpg?q=70",
    #         "mention_role": "1007318944568324136",  # testers
    #         "event_footer": "Storm King's Thunder session reminder"
    #     }
    # },
}

EMAIL_NAMES = {
    # Me
    'tommcn.14@gmail.com': 'Thomas',

    # Twilight Company / Droop Troop
    'sovietvvinter@gmail.com': 'Brett',
    'cspears107@gmail.com': 'Chey',
    'edmund.metzold@gmail.com': 'Edmund',
    'gabepack21@gmail.com': 'Gabe',
    'grahammartinb@gmail.com': 'Graham',
}


class CalendarExtension(Extension):
    @slash_command(
        name="remind_me",
        description="Remind me about any upcoming DnD events in this channel and refresh recent reminders.",
    )
    async def remind_me(self, ctx: SlashContext):
        print("Refreshing DnD reminders for /remind_me slash command.")
        await self.refresh_dnd_reminders()

        await ctx.send("Refreshed DnD reminders.", ephemeral=True)

    @listen()
    async def on_component(self, event: Component):
        ctx = event.ctx

        match ctx.custom_id:
            case "refresh_dnd_reminders":
                print("Refreshing DnD reminders for Refresh button click.")
                await self.refresh_dnd_reminders()

                await ctx.send("Refreshed DnD reminders.", ephemeral=True)

    @Task.create(TimeTrigger(hour=12, utc=True))
    async def remind_dnd_events(self):
        print("Refreshing DnD reminders for daily scheduled task.")
        await self.refresh_dnd_reminders()

    async def refresh_dnd_reminders(self):
        # Get calendar events
        events = GoogleCalendar.get_todays_events()

        for guild_id in EVENT_GUILD_CHANNEL_CONFIG:
            event_channels = EVENT_GUILD_CHANNEL_CONFIG[guild_id]
            for channel_id in event_channels:
                channel_config = event_channels[channel_id]

                event = find_event_with_prefix(events, channel_config['title_prefix'])

                if event:
                    await self.send_event_reminder(guild_id, channel_id, event)

    async def send_event_reminder(self, guild_id: str, channel_id: str, event: dict):
        channel_config: dict = EVENT_GUILD_CHANNEL_CONFIG[guild_id][channel_id]

        channel = self.bot.get_channel(channel_id)
        # Mention a role if specified.
        content = ' '
        if 'mention_role' in channel_config:
            guild = self.bot.get_guild(guild_id)
            role = guild.get_role(channel_config['mention_role'])
            content = role.mention
        embed = make_reminder_card(event, channel_config)
        components = make_reminder_components()

        existing_reminder: Optional[Message] = await self.find_last_event_reminder(channel)
        if existing_reminder is not None and existing_reminder.embeds[0].title == embed.title:
            # Edit the existing reminder message for this event if it has changed.
            if embed != existing_reminder.embeds[0]\
                    or content != existing_reminder.content\
                    or components != existing_reminder.components:
                await existing_reminder.edit(content=content,
                                             embed=embed,
                                             components=components)
        else:
            # Send a new reminder message for this event.
            await channel.send(content=content,
                               embed=embed,
                               components=components)

    async def find_last_event_reminder(self, channel: "TYPE_ALL_CHANNEL") -> Optional[Message]:
        return await find_matching_bot_message(channel, self.bot,
                                               match_condition=lambda msg: message_is_event_reminder(msg))


def setup(bot):
    CalendarExtension(bot)


class GoogleCalendar:
    @staticmethod
    def get_todays_events() -> [dict]:
        try:
            gcal_client = GoogleCalendar.google_calendar_client()

            # Look for events in the next 24 hours
            now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            tomorrow = (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'

            # Call the Calendar API
            print('Fetching Google Calendar events for the next 24 hours')
            events_result = gcal_client.events().list(calendarId='primary', timeMin=now, timeMax=tomorrow,
                                                      maxResults=20, singleEvents=True,
                                                      orderBy='startTime').execute()

            # Debug Logging for calendar events
            # for event in events_result.get('items', []):
            #     start = event['start'].get('dateTime', event['start'].get('date'))
            #     print(event['summary'], start)

            return events_result.get('items', [])
        except HttpError as error:
            print('An error occurred getting calendar events: %s' % error)

    @staticmethod
    def google_calendar_client():
        creds = None

        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('google-credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        try:
            return build('calendar', 'v3', credentials=creds)
        except HttpError as error:
            print('An error occurred getting google calendar client: %s' % error)


def find_event_with_prefix(events: [dict], title_prefix: str):
    for event in events:
        title: string = event['summary']
        if title.startswith(title_prefix):
            return event

    return None


def make_reminder_card(calendar_event: dict, channel_data: dict) -> Embed:
    print(calendar_event)

    card = Embed(
        title=calendar_event['summary'],
        color=BrandColors.YELLOW,
        description=calendar_event['description'],
    )

    # Add an image if appropriate
    if 'event_image' in channel_data:
        card.add_image(channel_data['event_image'])

    # Show the event time
    card.add_field(name="Time",
                   value=iso_to_discord_timestamp(calendar_event['start']).format(TimestampStyles.LongDateTime) + ' - '
                         + iso_to_discord_timestamp(calendar_event['end']).format(TimestampStyles.ShortTime)
                         + '\n🕓 '
                         + iso_to_discord_timestamp(calendar_event['start']).format(TimestampStyles.RelativeTime)
                   )

    # Show the attendee responses
    response_user_lists = get_response_user_lists(calendar_event['attendees'])
    card.add_field(name=':white_check_mark: Accepted', value=response_user_lists['accepted'], inline=True)
    card.add_field(name=':x: Declined', value=response_user_lists['declined'], inline=True)
    card.add_field(name=':grey_question: Unconfirmed', value=response_user_lists['needsAction'], inline=True)

    if 'event_footer' in channel_data:
        card.set_footer(text=channel_data['event_footer'] + ' (DnD Event reminder)')

    return card


def iso_to_discord_timestamp(calendar_time_dict) -> Timestamp:
    return Timestamp.fromisoformat(calendar_time_dict['dateTime'])


def get_response_user_lists(attendees) -> dict[str: str]:
    """
    Takes the attendees block from a Google Calendar event and generates a
    """
    response_lists = {'accepted': [], 'declined': [], 'needsAction': []}

    for attendee in attendees:
        name = attendee['email']
        if name in EMAIL_NAMES:
            name = EMAIL_NAMES[name]

        response_status = attendee['responseStatus']
        if response_status not in response_lists:
            response_status = 'needsAction'

        response_lists[response_status].append(name)

    # Sort responses alphabetically by name
    for response_list in response_lists.values():
        response_list.sort()

    return {response_status: ('> ' + '\n> '.join(names) + ' ') if names else '-'
            for (response_status, names) in response_lists.items()}


def message_is_event_reminder(message: Message) -> bool:
    if message.embeds is None or len(message.embeds) == 0:
        return False

    card: Embed = message.embeds[0]
    if card.footer is None or card.footer.text is None:
        return False
    return card.footer.text.endswith('(DnD Event reminder)')


def make_reminder_components():
    return Button(
        custom_id="refresh_dnd_reminders",
        style=ButtonStyle.BLUE,
        label="Refresh",
        emoji=PartialEmoji.from_str(':repeat:')
    )
