from utils import Account, ExternalCalendar, Attendee
from rules_and_filters import Filter, Rule

uni_classes = ExternalCalendar.from_url("https://some-url.com/some-path.ics")

personal = Account.from_email("your.email@gmail.com")
work = Account.from_email("your.email@work.com")


# ======================== UNI CLASSES ========================
print("Uni Classes")
personal_uniclasses = personal.calendar("Uni Classes", create=True)

personal_uniclasses.add_events(
    uni_classes.events().apply(
        Rule.add_attendees([Attendee(email=personal_uniclasses.id)])
    )
)

# ======================== SUBSCRIPTIONS ========================
work.subscribe_internal(
    personal.calendar("your.email@gmail.com"),
    summary_override="Personal",
)
