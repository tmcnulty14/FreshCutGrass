import os.path
import string
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from interactions import Extension, Task, TimeTrigger, Embed, BrandColors, Timestamp, TimestampStyles

# Google API scope
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

EVENT_GUILD_CHANNEL_PREFIXES = {
    # Edmung Us server
    "771115921443651615": {
        # droop-troop channel
        "803481288870461500": {
            "title_prefix": "D&D TC",
            "event_image": "https://images.ctfassets.net/swt2dsco9mfe/48Nfrlty0IQe0NdGu3IvIq"
                           "/30fa851afad405a68fa247b13ea55b87/1920x1342-skt.jpg?q=70",
            "mention_role": "805283535186296892",  # DROOP TROOP
            "event_footer": "Storm King's Thunder session reminder"
        }
    },
    # Bot Testing server
    "834548590399586365": {
        # general channel
        "834548590940520491": {
            "title_prefix": "D&D TC",
            "event_image": "https://images.ctfassets.net/swt2dsco9mfe/48Nfrlty0IQe0NdGu3IvIq"
                           "/30fa851afad405a68fa247b13ea55b87/1920x1342-skt.jpg?q=70",
            "mention_role": "1007318944568324136",  # testers
            "event_footer": "Storm King's Thunder session reminder"
        }
    },
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
    @Task.create(TimeTrigger(hour=12, utc=True))
    async def remind_dnd_events(self):
        # Get calendar events
        events = get_todays_events()

        for guild_id in EVENT_GUILD_CHANNEL_PREFIXES:
            event_channels = EVENT_GUILD_CHANNEL_PREFIXES[guild_id]
            for channel_id in event_channels:
                channel_data = event_channels[channel_id]

                event = find_event_with_prefix(events, channel_data['title_prefix'])

                if event:
                    channel = self.bot.get_channel(channel_id)

                    # Mention a role if specified.
                    message = ' '
                    if 'mention_role' in channel_data:
                        guild = self.bot.get_guild(guild_id)
                        role = guild.get_role(channel_data['mention_role'])
                        message = role.mention

                    await channel.send(content=message,
                                       embed=make_reminder_card(event, channel_data))


def setup(bot):
    CalendarExtension(bot)


def get_todays_events():
    try:
        gcal_client = google_calendar_client()

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


def find_event_with_prefix(events, title_prefix):
    for event in events:
        title: string = event['summary']
        if title.startswith(title_prefix):
            return event

    return None


def make_reminder_card(calendar_event, channel_data):
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
        card.set_footer(text=channel_data['event_footer'])

    return card


def iso_to_discord_timestamp(calendar_time_dict):
    return Timestamp.fromisoformat(calendar_time_dict['dateTime'])


def get_response_user_lists(attendees):
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
