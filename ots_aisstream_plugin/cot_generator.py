import datetime
from xml.etree.ElementTree import Element, SubElement
from opentakserver.functions import iso8601_string_from_datetime


UNKNOWN = "9999999.0"


def generate_event(start_time: datetime.datetime, stale_time: datetime.datetime, uid: str, cot_type="a-f-G-U-C", how="h-e") -> Element:
    return Element("event", {"start": iso8601_string_from_datetime(start_time), "time": iso8601_string_from_datetime(stale_time),
                   "stale": iso8601_string_from_datetime(stale_time), "uid": str(uid), "type": cot_type, "how": how})


def generate_point(event: Element, lat=UNKNOWN, lon=UNKNOWN, ce=UNKNOWN, hae=UNKNOWN, le=UNKNOWN) -> Element:
    SubElement(event, "point", {"lat": str(lat), "lon": str(lon), "ce": str(ce), "hae": str(hae), "le": str(le)})
    return event


def add_detail(event: Element, tag_name: str, attributes: dict[str, str], text: str = None) -> Element:
    detail = event.find("detail")
    if not detail:
        detail = SubElement(event, "detail")

    SubElement(detail, tag_name, attributes).text = text

    if not event.find("detail"):
        event.append(detail)
    return event
