from dataclasses import dataclass
from functools import cached_property
import re
from typing import List, Literal, Optional, Union
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import json
from dotenv import load_dotenv
from icalendar import Calendar, Event, vCalAddress
from datetime import datetime
import pytz
import os
import os

import requests


def slugify(s):
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    s = s.replace("-", "")
    return s


load_dotenv("../.env")


class EventsList:
    def __init__(self, events):
        self.events = events

    def __iter__(self) -> List[Event]:
        return iter(self.events)

    def __len__(self):
        return len(self.events)

    def __repr__(self):
        return self.events.__repr__()

    def filter(self, function: callable):
        return EventsList(list(filter(function, self.events)))

    def apply(self, function: callable):
        return EventsList([function(event) for event in self.events])


@dataclass
class Attendee:
    display_name: str = ""
    email: str = ""
    comment: str = ""
    response_status: str = "needsAction"
    optional: bool = True
    resource: bool = False

    @staticmethod
    def from_gcal(gcal_attendee: dict):
        return Attendee(
            display_name=gcal_attendee.get("displayName"),
            email=gcal_attendee.get("email"),
            comment=gcal_attendee.get("comment"),
            response_status=gcal_attendee.get("responseStatus"),
            optional=gcal_attendee.get("optional"),
            resource=gcal_attendee.get("resource"),
        )

    def to_gcal(self):
        return {
            "displayName": self.display_name,
            "email": self.email,
            "comment": self.comment,
            "responseStatus": self.response_status,
            "optional": self.optional,
        }

    @staticmethod
    def from_ical(ical_attendee: dict):
        return Attendee(
            display_name=ical_attendee["displayName"],
            email=ical_attendee["email"],
            comment=ical_attendee["comment"],
            response_status=ical_attendee["responseStatus"],
            optional=ical_attendee["optional"],
            resource=ical_attendee["resource"],
        )
    
    def __eq__(self, other: object) -> bool:
        e1 = (
            self.email,
            self.optional,
        )
        e2 = (
            other.email,
            other.optional,
        )
        return e1 == e2


@dataclass
class Event:
    origin: Union[Literal["gcal"], Literal["ical"]]
    summary: str
    location: str
    start: datetime
    end: datetime
    description: str
    attendees: List[Attendee]
    id: Optional[str]
    iCalUID: str
    last_modified: datetime
    transparency: str
    sequence: int
    status: Union[Literal["confirmed"], Literal["tentative"], Literal["cancelled"]]
    is_all_day: bool = False
    source: Optional[str] = None

    def __eq__(self, other: "Event"):
        e1 = (
            self.summary,
            self.location,
            self.start.replace(tzinfo=None).isoformat(),
            self.end.replace(tzinfo=None).isoformat(),
            tuple(self.attendees),
            self.transparency,
            self.status,
            self.is_all_day,
        )
        e2 = (
            other.summary,
            other.location,
            other.start.replace(tzinfo=None).isoformat(),
            other.end.replace(tzinfo=None).isoformat(),
            tuple(other.attendees),
            other.transparency,
            other.status,
            other.is_all_day,
        )
        if e1 != e2:
            for i in range(len(e1)):
                if e1[i] != e2[i]:
                    print(i)
            print(e1)
            print(e2)
        return e1 == e2

    @property
    def uuid(self):
        if self.origin == "gcal":
            return slugify(self.id.replace("_", "ab"))
        elif self.origin == "ical":
            return slugify(f"{self.iCalUID}{self.sequence}".replace("_", "ab"))

    @staticmethod
    def from_gcal(gcal_event: dict):
        def from_rfc3339(rfc3339: str):
            return datetime.strptime(rfc3339, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=pytz.UTC
            )

        def get_datetime(obj: dict):
            dt = None
            if "date" in obj:
                dt = datetime.fromisoformat(obj["date"])
            elif "dateTime" in obj:
                try:
                    dt = datetime.fromisoformat(obj["dateTime"])
                except ValueError:
                    dt = datetime.strptime(obj["dateTime"], "%Y-%m-%dT%H:%M:%SZ")
            else:
                raise ValueError("Invalid datetime object")
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            return dt

        def is_all_day():
            if "date" in gcal_event["start"] and "date" in gcal_event["end"]:
                return True
            elif "dateTime" in gcal_event["start"] and "dateTime" in gcal_event["end"]:
                return False
            else:
                raise ValueError("Invalid datetime object")

        try:
            if "summary" not in gcal_event:
                return None
            return Event(
                origin="gcal",
                summary=gcal_event["summary"],
                location=gcal_event.get("location"),
                start=get_datetime(gcal_event["start"]),
                end=get_datetime(gcal_event["end"]),
                is_all_day=is_all_day(),
                description=gcal_event.get("description"),
                attendees=[
                    Attendee.from_gcal(att) for att in gcal_event.get("attendees", [])
                ],
                iCalUID=gcal_event["iCalUID"],
                id=gcal_event["id"],
                last_modified=from_rfc3339(gcal_event["updated"]),
                transparency=gcal_event.get("transparency", "opaque"),
                sequence=gcal_event["sequence"],
                status=gcal_event["status"],
            )
        except Exception as e:
            print(gcal_event)
            raise e

    def to_gcal(self):
        def clean_format(string: Optional[str]):
            if string is None:
                return None
            return string.replace("\n", "\\n")

        def date(date: datetime):
            # If all day, convert to yyyy-mm-dd, else convert to isoformat
            if self.is_all_day:
                return {"date": date.strftime("%Y-%m-%d")}
            else:
                return {"dateTime": date.isoformat()}

        return {
            "summary": clean_format(self.summary),
            "location": clean_format(self.location),
            "description": clean_format(self.description),
            "start": date(self.start),
            "end": date(self.end),
            "attendees": [att.to_gcal() for att in self.attendees],
            "reminders": {
                "useDefault": True,
            },
            "id": self.uuid,
            # "sequence": self.sequence,
            "transparency": self.transparency,
            "status": self.status,
        }

    @staticmethod
    def from_ical(
        comp,
    ):
        def get_utc_time(dt: datetime) -> datetime:
            return datetime.fromisoformat(dt.isoformat())

        event = {}

        for name, prop in comp.property_items():
            if name == "LAST-MODIFIED":
                event["last_modified"] = datetime.fromisoformat(prop.dt.isoformat())

            if name == "UID":
                event["iCalUID"] = prop.to_ical().decode("utf-8")

            if name == "SUMMARY":
                event["summary"] = prop.to_ical().decode("utf-8")

            if name == "LOCATION":
                event["location"] = prop.to_ical().decode("utf-8")

            elif name == "DTSTART":
                event["start"] = get_utc_time(prop.dt)

            elif name == "DTEND":
                event["end"] = get_utc_time(prop.dt)

            elif name == "SEQUENCE":
                event["sequence"] = prop

            elif name == "TRANSP":
                event["transparency"] = prop.lower()

            # elif name == 'CLASS':
            #     event['visibility'] = prop.lower()

            # elif name == 'ORGANIZER':
            #     event['organizer'] = {
            #         'displayName': prop.params.get('CN') or '',
            #         'email': re.match('mailto:(.*)', prop).group(1) or ''
            #     }

            elif name == "DESCRIPTION":
                desc = prop.to_ical().decode("utf-8")
                desc = desc.replace("\xa0", " ")
                if "description" in event:
                    event["description"] = desc + "\r\n" + event["description"]
                else:
                    event["description"] = desc

            # elif name == 'X-ALT-DESC' and 'description' not in event:
            #     soup = BeautifulSoup(prop, 'lxml')
            #     desc = soup.body.text.replace(u'\xa0', u' ')
            #     if 'description' in event:
            #         event['description'] += '\r\n' + desc
            #     else:
            #         event['description'] = desc

            elif name == "ATTENDEE":
                if "attendees" not in event:
                    event["attendees"] = []
                RSVP = prop.params.get("RSVP") or ""
                RSVP = "RSVP={}".format(
                    "TRUE:{}".format(prop) if RSVP == "TRUE" else RSVP
                )
                ROLE = prop.params.get("ROLE") or ""
                event["attendees"].append(
                    Attendee(
                        display_name=prop.params.get("CN") or "",
                        email=re.match("mailto:(.*)", prop).group(1) or "",
                        comment=ROLE,
                    )
                )

            # VALARM: only remind by UI popup
            # elif name == 'ACTION':
            #     event['reminders'] = {'useDefault': True}

            # else:
            #     # print(name)
            #     pass

        event.setdefault("attendees", [])
        event.setdefault("id", None)
        event.setdefault("transparency", "opaque")
        event.setdefault("description", "")
        event.setdefault("sequence", 0)
        event.setdefault("status", "confirmed")
        return Event(origin="ical", **event)

    def to_ical(self):
        cal = Calendar()
        cal.add("prodid", "-//Google Inc//Google Calendar 70.9054//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("X-WR-CALNAME", "My Calendar")
        cal.add("X-WR-TIMEZONE", "Europe/Berlin")

        event = Event()
        event.add("summary", self.summary)
        event.add("location", self.location)
        event.add("dtstart", self.start)
        event.add("dtend", self.end)
        event.add("description", self.description)
        event.add("last-modified", self.last_modified)
        event.add("uid", self.iCalUID)
        event.add("sequence", 0)
        event.add("transp", "OPAQUE")
        event.add("status", "CONFIRMED")
        event.add("class", "PUBLIC")
        event.add("created", self.last_modified)
        event.add("dtstamp", self.last_modified)
        event.add("organizer", vCalAddress("mailto:"))
        for attendee in self.attendees:
            event.add("attendee", attendee, encode=0)
        event.add("priority", 5)
        event.add("X-APPLE-TRAVEL-ADVISORY-BEHAVIOR", "AUTOMATIC")
        cal.add_component(event)

        return cal.to_ical()

    def to_ical_str(self):
        return self.to_ical().decode("utf-8")


def _parse_ics(calendar: Calendar) -> List[Event]:
    events = []

    for i, comp in enumerate(calendar.walk("VEVENT")):
        events.append(Event.from_ical(comp))

    return events


@dataclass
class InternalCalendar:
    account: "Account"
    id: str
    name: str
    _events: str = None  # Used for caching

    @property
    def service(self):
        return self.account.service

    def _upsert_acl_rule(self, rule: dict):
        self.service.acl().insert(calendarId=self.id, body=rule).execute()

    def events(self) -> EventsList:
        if self._events is not None:
            return EventsList(self._events)
        events_list = []
        kwargs = {"timeZone": "UTC"}
        # Get all events from all pages
        while True:
            events = self.service.events().list(calendarId=self.id, **kwargs).execute()
            events_list += [Event.from_gcal(e) for e in events["items"]]
            if events.get("nextPageToken") is None:
                break
            kwargs["pageToken"] = events["nextPageToken"]

        # Remove None values
        events_list = [e for e in events_list if e is not None]
        self._events = events_list
        return EventsList(events_list)

    def add_events(self, events: List[Event]):
        own_events = self.events()
        uuid_mapping = {event.uuid: event for event in own_events}
        id_set = {event.id for event in own_events}

        for event in events:
            if event.uuid in uuid_mapping:
                # Update if more recent
                if event != uuid_mapping[event.uuid]:
                    print(f"Updating event {event.summary}")
                    self.service.events().update(
                        calendarId=self.id,
                        eventId=event.uuid,
                        body=event.to_gcal(),
                    ).execute()
                    self._events = None  # Clear cache

            else:
                try:
                    # Insert new
                    self.service.events().insert(
                        calendarId=self.id, body=event.to_gcal()
                    ).execute()
                    self._events = None  # Clear cache
                    print(
                        f"Inserting event `{event.summary}`",
                    )
                except Exception as e:
                    print("ERROR INSERTING EVENT", event, event.uuid)
                    print(e)
                    pass

    def sync_events(self):
        pass

    def clear(self):
        events = self.events()

        def delete(event: Event):
            print("DELETING EVENT", event.summary)
            self.service.events().delete(
                calendarId=self.id, eventId=event.uuid
            ).execute()

        for event in events:
            delete(event)


@dataclass
class Account:
    email: str
    credentials: Credentials = None
    _accounts = {}

    @staticmethod
    def from_email(email: str, provider="google"):
        return Account.from_credentials_file(f"../tokens/{email}.json")

    @staticmethod
    def from_credentials_file(credentials_file: str):
        with open(credentials_file, "r") as f:
            creds = json.load(f)
        credentials = Credentials(
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            token=creds["token"]["access_token"],
            refresh_token=creds["token"]["refresh_token"],
            token_uri=os.getenv("GOOGLE_TOKEN_URI"),
        )
        return Account(credentials=credentials, email=creds["jwtData"]["email"])

    @cached_property
    def calendar_list(self):
        return self.service.calendarList().list(showHidden=True).execute()

    @cached_property
    def service(self):
        service = build("calendar", "v3", credentials=self.credentials)
        return service

    def calendar(self, name: str, create: bool = False) -> InternalCalendar:
        for calendar in self.calendar_list["items"]:
            if calendar["summary"] == name:
                # Cache the calendar in the _accounts dict
                # Usefull because the calendar object caches the events
                id = calendar["id"]
                if id in self._accounts:
                    return self._accounts[id]
                c = InternalCalendar(account=self, id=id, name=name)
                self._accounts[id] = c
                return c

        if not create:
            raise Exception(f"Calendar '{name}' not found")

        # Create calendar
        print(f"Creating calendar `{name}`")
        response = (
            self.service.calendars()
            .insert(
                body={
                    "summary": name,
                }
            )
            .execute()
        )

        # Uncache calendar list
        self.__dict__.pop("calendar_list")
        return self.calendar(name, create=False)

    def subscribe_internal(
        self,
        calendar: InternalCalendar,
        role: Union[Literal["owner"], Literal["reader"], Literal["writer"]] = "reader",
        summary_override: str = None,
    ):
        """
        Will subscribe this Account to the given calendar.

        - Create an ACL rule for the calendar if needed.
        - Add the calendar to the calendar list of this account.
        """
        assert calendar.account.email != self.email, "Cannot subscribe to own calendar"

        rule = {
            "scope": {
                "type": "user",
                "value": self.email,
            },
            "role": role,
        }

        calendar._upsert_acl_rule(rule)
        self.service.calendarList().insert(
            body={
                "id": calendar.id,
                "summaryOverride": summary_override,
            }
        ).execute()

        self.service.calendarList().update(
            calendarId=calendar.id,
            body={
                "summaryOverride": summary_override,
            },
        ).execute()

        pass


@dataclass
class ExternalCalendar:
    url: str = None

    @staticmethod
    def from_url(url: str):
        return ExternalCalendar(url=url)

    @cached_property
    def calendar(self) -> Calendar:
        # Construct Calendar from url and get events
        gcal = Calendar.from_ical(requests.get(self.url).text)
        return gcal

    def events(self):
        return EventsList(_parse_ics(self.calendar))
