import datetime
import json
import traceback
import uuid

from xml.etree.ElementTree import tostring
import pika
from websocket import WebSocketApp
from opentakserver.extensions import logger
from .cot_generator import *
from .rabbitmq_client import RabbitMQClient
from flask import Flask


class WebsocketWrapper(RabbitMQClient):
    def __init__(self, app: Flask) -> None:
        super().__init__(app)
        self._config = {}
        self._web_sock: WebSocketApp
        self._shutdown = False

    # Inherited from RabbitMQClient
    def on_channel_open(self, channel):
        logger.debug("RabbitMQ Channel Opened")
        self.rabbit_channel = channel

    # Inherited from RabbitMQClient
    def on_message(self, unused_channel, basic_deliver, properties, body):
        logger.debug(f"Got message from RabbitMQ: {body}")

    def on_websocket_message(self, web_sock: WebSocketApp, message: str) -> None:
        try:
            message = json.loads(message)
            cot = self.generate_cot(message)
            body = {'uid': self._app.config.get("OTS_NODE_ID"), 'cot': tostring(cot).decode('utf-8')}
            self.rabbit_channel.basic_publish(exchange='cot_controller', routing_key='',
                                              body=json.dumps(body),
                                              properties=pika.BasicProperties(
                                                  expiration=self._app.config.get("OTS_RABBITMQ_TTL")))
        except BaseException as e:
            logger.error(f"message failed: {e}")
            logger.error(traceback.format_exc())

    def on_websocket_open(self, web_sock: WebSocketApp) -> None:
        logger.info("AISStream websocket opened")
        subscribe_message = {"APIKey": self._config.get("OTS_AISSTREAM_PLUGIN_API_KEY"),
                             "BoundingBoxes": self._config.get("OTS_AISSTREAM_PLUGIN_BBOX"),
                             "FilterMessageTypes": ["PositionReport"]}

        subscribe_message_json = json.dumps(subscribe_message)
        web_sock.send(subscribe_message_json)

    def on_websocket_error(self, web_sock: WebSocketApp, error_message: str) -> None:
        pass

    def on_websocket_close(self, web_sock: WebSocketApp, close_status_code: int, close_msg: str) -> None:
        pass

    def stop(self):
        self._web_sock.close()
        self._shutdown = True

    def ws_thread(self, url: str, config: dict) -> None:
        while not self._shutdown:
            self._config = config
            self._web_sock = WebSocketApp(
                url=url,
                on_open=self.on_websocket_open,
                on_close=self.on_websocket_close,
                on_message=self.on_websocket_message,
                on_error=self.on_websocket_error,
            )
            self._web_sock.run_forever()

    def generate_cot(self, message: dict) -> Element:
        if message.get("MessageType") == "PositionReport":
            metadata = message.get("MetaData")
            position_report = message.get("Message").get("PositionReport")
            if not metadata:
                logger.debug("AISStream message doesn't include metadata")
                return

            lat = str(metadata.get("latitude")) or UNKNOWN
            lon = str(metadata.get("longitude")) or UNKNOWN
            mmsi = str(metadata.get("MMSI") or str(uuid.uuid4()))
            ship_name = metadata.get("ShipName") or ""
            ship_name = ship_name.strip()
            try:
                timestamp = datetime.datetime.strptime(metadata.get("time_utc"), "%Y-%m-%d %H:%M:%S.%f %z %Z")
            except ValueError:
                timestamp = datetime.datetime.now(datetime.timezone.utc)

            event = generate_event(timestamp, timestamp + datetime.timedelta(hours=1), mmsi, self._config.get("OTS_AISSTREAM_PLUGIN_COT_TYPE"), "m-g")
            event = generate_point(event, lat, lon)
            event = add_detail(event, "track", {"course": str(position_report.get("Cog")) or "0.0", "speed": str(position_report.get("Sog")) or "0.0"})
            event = add_detail(event, "contact", {"callsign": ship_name})
            event = add_detail(event, "remarks", {}, f"Name: {ship_name}, MMSI: {mmsi}")
            return event
