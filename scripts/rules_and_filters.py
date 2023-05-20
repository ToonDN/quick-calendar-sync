import re
from typing import List, Tuple
from utils import Event, Attendee

class Filter:
    @staticmethod
    def on_attending(email):
        def filter(event: Event):
            if len(event.attendees) == 0:
                return True
            att = None
            for attendee in event.attendees:
                if attendee.email == email:
                    att = attendee
                    break
            if att is not None:
                return att.response_status == "accepted"
            return False

        return filter

    @staticmethod
    def duration(max_minutes, min_minutes=0):
        def filter(event: Event):
            duration = (event.end - event.start).total_seconds() / 60
            return duration <= max_minutes and duration >= min_minutes
        return filter


class Rule:
    @staticmethod
    def remove_attendees():
        def rule(event: Event):
            event.attendees = []
            return event

        return rule

    @staticmethod
    def add_prefix(prefix):
        def add(event: Event):
            event.summary = prefix + event.summary
            return event

        return add

    @staticmethod
    def regex_colorizer(regex_color_mapping: List[Tuple[str, str]]):
        """
        Will colorize the event summary based on the regex_color_mapping.
        The first matching regex will be used.
        """

        def rule(event: Event):
            for regex, color in regex_color_mapping:
                match = re.match(regex, event.summary)
                if match:
                    break

            return event

        return rule

    @staticmethod
    def add_attendees(attendees: List[Attendee]):
        def rule(event: Event):
            event.attendees.extend(attendees)
            return event

        return rule