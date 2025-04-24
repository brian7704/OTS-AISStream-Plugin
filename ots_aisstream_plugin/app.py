import os
import pathlib
import threading
import traceback

from dataclasses import dataclass

import yaml
from flask import Blueprint, send_from_directory, jsonify, Flask, current_app as app, request
from flask_security import roles_accepted
from opentakserver.plugins.Plugin import Plugin
from opentakserver.extensions import *

from .WebsocketWrapper import WebsocketWrapper
from .default_config import DefaultConfig
import importlib.metadata


@dataclass
class AISStreamPlugin(Plugin):
    # Change the Blueprint name to YourPluginBlueprint
    url_prefix = f"/api/plugins/{pathlib.Path(__file__).resolve().parent.name}"
    blueprint = Blueprint("AISStreamPlugin", __name__, url_prefix=url_prefix)

    def __init__(self):
        super().__init__()
        self._websocket_wrapper: WebsocketWrapper | None = None
        self._ws_thread: threading.Thread | None = None
        self.load_metadata()

    def activate(self, context: Flask, enabled: bool = True):
        self._app = context
        self._load_config(DefaultConfig)
        self._websocket_wrapper = WebsocketWrapper(self._app)

        if enabled:
            try:
                self._ws_thread = threading.Thread(
                    target=self._websocket_wrapper.ws_thread,
                    kwargs={"url": "wss://stream.aisstream.io/v0/stream", "config": self._config},
                )
                self._ws_thread.start()

                logger.info(f"Successfully Loaded {self.name}")
            except BaseException as e:
                logger.error(f"Failed to load {self.name}: {e}")
                logger.error(traceback.format_exc())
        else:
            logger.info(f"Plugin {self.name} is disabled")

    def load_metadata(self):
        try:
            distributions = importlib.metadata.packages_distributions()
            for distro in distributions:
                if str(__name__).startswith(distro):
                    self.name = distributions[distro][0]
                    self.distro = distro
                    info = importlib.metadata.metadata(self.distro)
                    self._metadata = info.json
                    return info.json

        except BaseException as e:
            logger.error(e)

    # Loads default config and user config from ~/ots/config.yml
    # In most cases you don't need to change this
    def _load_config(self, DefaultConfig):
        # Gets default config key/value pairs from the plugin's default_config.py
        for key in dir(DefaultConfig):
            if key.isupper():
                self._config[key] = getattr(DefaultConfig, key)
                self._app.config.update({key: getattr(DefaultConfig, key)})

        # Get user overrides from config.yml
        with open(os.path.join(self._app.config.get("OTS_DATA_FOLDER"), "config.yml")) as yaml_file:
            yaml_config = yaml.safe_load(yaml_file)
            for key in self._config.keys():
                value = yaml_config.get(key)
                if value:
                    self._config[key] = value
                    self._app.config.update({key: value})

    def stop(self):
        if self._websocket_wrapper:
            self._websocket_wrapper.stop()
            self._websocket_wrapper = None
        self._ws_thread = None

    def get_info(self):
        self.load_metadata()
        self.get_plugin_routes(self.url_prefix)
        return {'name': self.name, 'distro': self.distro, 'routes': self.routes}

    # Make route methods static to avoid "no-self-use" errors
    # OpenTAKServer's web UI will call your plugin's /ui endpoint and display the results
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/ui")
    def ui():
        return '', 200

    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route('/assets/<file_name>')
    def serve(file_name):
        logger.debug(f"Path: {file_name}")
        dist = f"../{pathlib.Path(__file__).parent.resolve().name}/dist/assets"
        logger.warning(os.path.join(pathlib.Path(__file__).parent.resolve(), "dist", "assets", file_name))
        if file_name != "" and os.path.exists(os.path.join(pathlib.Path(__file__).parent.resolve(), "dist", "assets", file_name)):
            logger.info(f"Serving {file_name}")
            return send_from_directory(dist, file_name)
        else:
            return send_from_directory(dist, 'index.html')

    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/config")
    def config():
        config = {}

        for key in dir(DefaultConfig):
            if key.isupper():
                config[key] = app.config.get(key)

        return jsonify(config)

    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/config", methods=["POST"])
    def update_config():
        try:
            result = DefaultConfig.update_config(request.json)
            if result["success"]:
                DefaultConfig.update_config(request.json)
                return jsonify(result)
            else:
                return jsonify(result), 400
        except BaseException as e:
            logger.error("Failed to update config:" + str(e))
            logger.error(traceback.format_exc())
            return jsonify({"success": False, "error": str(e)}), 400
