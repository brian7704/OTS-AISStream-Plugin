import json

from websocket import WebSocketApp
from opentakserver.extensions import logger


class WebsocketWrapper:
    def __init__(self) -> None:
        self._config = {}
        self._web_sock: WebSocketApp
        self._shutdown = False

    def on_message(self, web_sock: WebSocketApp, message: str) -> None:
        logger.info(f"Got message: {message}")

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
