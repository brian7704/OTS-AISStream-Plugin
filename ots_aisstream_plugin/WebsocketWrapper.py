import datetime
import json
import uuid

import opentakserver.functions
from websocket import WebSocketApp
from opentakserver.extensions import logger
import aiscot
from xml.etree.ElementTree import Element, SubElement


class WebsocketWrapper:
    def __init__(self) -> None:
        self._config = {}
        self._web_sock: WebSocketApp
        self._shutdown = False

    def on_message(self, web_sock: WebSocketApp, message: str) -> None:
        #logger.info(f"Got message: {message}")
        #logger.warning(aiscot.ais_to_cot(json.loads(message), None, None))
        return

    def on_open(self, web_sock: WebSocketApp) -> None:
        logger.info("on_open")
        subscribe_message = {"APIKey": self._config.get("OTS_AISSTREAM_PLUGIN_API_KEY"),
                             "BoundingBoxes": self._config.get("OTS_AISSTREAM_PLUGIN_BBOX"),
                             "FilterMessageTypes": ["PositionReport"]}

        subscribe_message_json = json.dumps(subscribe_message)
        web_sock.send(subscribe_message_json)

    def on_error(self, web_sock: WebSocketApp, error_message: str) -> None:
        pass

    def on_close(self, web_sock: WebSocketApp, close_status_code: int, close_msg: str) -> None:
        pass

    def stop(self):
        self._web_sock.close()
        self._shutdown = True

    def ws_thread(self, url: str, config: dict) -> None:
        while not self._shutdown:
            self._config = config
            self._web_sock = WebSocketApp(
                url=url,
                on_open=self.on_open,
                on_close=self.on_close,
                on_message=self.on_message,
                on_error=self.on_error,
            )
            self._web_sock.run_forever()

    def generate_cot(self, message: dict) -> None:
        if message.get("MessageType") == "PositionReport":
            now = opentakserver.functions.iso8601_string_from_datetime(datetime.datetime.now(datetime.timezone.utc))
            stale = opentakserver.functions.iso8601_string_from_datetime(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10))

            metadata = message.get("MetaData")
            position_report = message.get("PositionReport")
            if not metadata:
                logger.debug("AISStream message doesn't include metadata")
                return

            lat = metadata.get("latitude") or "0.0"
            lon = metadata.get("longitude") or "0.0"
            mmsi = metadata.get("MMSI") or ""
            ship_name = metadata.get("ShipName") or ""
            try:
                timestamp = datetime.datetime.strptime(metadata.get("time_utc"), "%Y-%m-%d %H:%M:%S.%f %z %Z")
            except ValueError:
                timestamp = opentakserver.functions.iso8601_string_from_datetime(datetime.datetime.now(datetime.timezone.utc))

            event = Element("event", {'how': 'm-g', 'type': self._config.get("OTS_AISSTREAM_PLUGIN_COT_TYPE"),
                                      "version": "2.0", "uid": str(uuid.uuid4()), "start": now, "stale": stale})
            latitude = message.get("")
            SubElement(event, "point", {"ce": "999999.0", "le": "999999.0", "hae": "999999.0", "lat": str(message.get(""))})
