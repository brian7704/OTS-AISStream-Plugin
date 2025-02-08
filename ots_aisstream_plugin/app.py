import os
import threading
import traceback

import yaml
from flask import Blueprint, render_template, jsonify, Flask
from opentakserver.plugins.Plugin import Plugin
from opentakserver.extensions import *

from .WebsocketWrapper import WebsocketWrapper
from .default_config import DefaultConfig
import importlib.metadata


class AISStreamPlugin(Plugin):
    # Use a URL prefix of "/api/your_plugin_name" and change the Blueprint name to YourPluginBlueprint
    blueprint = Blueprint("AISStreamPlugin", __name__, url_prefix="/api/plugins/ais_stream_plugin", template_folder="templates")

    def __init__(self):
        self._app: Flask | None = None
        self._config = {}
        self._metadata = {}
        self._name = ""
        self._websocket_wrapper = WebsocketWrapper()

    def activate(self, app: Flask):
        self._app = app
        self._load_config()
        self._load_metadata()

        try:
            _ws_thread = threading.Thread(
                target=self._websocket_wrapper.ws_thread,
                kwargs={"url": "wss://stream.aisstream.io/v0/stream", "config": self._config},
            )
            _ws_thread.start()

            logger.info(f"Successfully Loaded {self._name}")
        except BaseException as e:
            logger.error(f"Failed to load {self._name}: {e}")
            logger.error(traceback.format_exc())

    # Loads default config and user config from ~/ots/config.yml
    # In most cases you don't need to change this
    def _load_config(self):
        # Gets default config key/value pairs from default_config.py
        for key in dir(DefaultConfig):
            if key.isupper():
                self._config[key] = getattr(DefaultConfig, key)

        # Get user overrides from config.yml
        with open(os.path.join(self._app.config.get("OTS_DATA_FOLDER"), "config.yml")) as yaml_file:
            yaml_config = yaml.safe_load(yaml_file)
            for key in self._config.keys():
                value = yaml_config.get(key)
                if value:
                    self._config[key] = value

    def _load_metadata(self):
        try:
            distribution = None
            distributions = importlib.metadata.packages_distributions()
            for distro in distributions:
                if str(__name__).startswith(distro):
                    distribution = distributions[distro][0]
                    break

            if distribution:
                info = importlib.metadata.metadata(distribution)
                self._metadata = info.json
                self._name = self._metadata.get("Name") or self._metadata.get("name")
            else:
                logger.error("Failed to get plugin name")
        except BaseException as e:
            logger.error(e)

    def stop(self):
        self._websocket_wrapper.stop()

    # Make route methods static to avoid "no-self-use" errors
    @staticmethod
    @blueprint.route("/")
    def plugin_info():  # Do not put "self" as a method parameter here
        # This method will return JSON with info about the plugin derived from pyproject.toml, please do not change it
        try:
            distribution = None
            distributions = importlib.metadata.packages_distributions()
            for distro in distributions:
                if str(__name__).startswith(distro):
                    distribution = distributions[distro][0]
                    break

            if distribution:
                info = importlib.metadata.metadata(distribution)
                return jsonify(info.json)
            else:
                return jsonify({'success': False, 'error': 'Plugin not found'}), 404
        except BaseException as e:
            logger.error(e)
            return jsonify({'success': False, 'error': e}), 500

    # OpenTAKServer's web UI will call your plugin's /ui endpoint and display the results
    @staticmethod
    @blueprint.route("/ui")
    def ui():
        return render_template("index.html")
