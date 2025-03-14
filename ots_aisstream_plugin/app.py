import os
import pathlib
import threading
import traceback

from dataclasses import dataclass

import mistune
import yaml
from flask import Blueprint, render_template, jsonify, Flask, current_app as app, request
from opentakserver.plugins.Plugin import Plugin
from opentakserver.extensions import *

from .WebsocketWrapper import WebsocketWrapper
from .default_config import DefaultConfig
import importlib.metadata


@dataclass
class AISStreamPlugin(Plugin):
    # Change the Blueprint name to YourPluginBlueprint
    url_prefix = f"/api/plugins/{pathlib.Path(__file__).resolve().parent.name}"
    blueprint = Blueprint("AISStreamPlugin", __name__, url_prefix=url_prefix, template_folder="templates")

    def __init__(self):
        super().__init__()
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
        self._websocket_wrapper.stop()

    def _load_metadata(self):
        try:
            distributions = importlib.metadata.packages_distributions()
            for distro in distributions:
                if str(__name__).startswith(distro):
                    self._name = distributions[distro][0]
                    self._distro = distro
                    info = importlib.metadata.metadata(self._distro)
                    self._metadata = info.json
                    break

        except BaseException as e:
            logger.error(e)

    def get_info(self):
        self._load_metadata()
        self.get_plugin_routes(self.url_prefix)
        return {'name': self._name, 'distro': self._distro, 'routes': self._routes}

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
        name = ""
        readme = ""
        documentation_link = ""
        repo_link = ""
        metadata = {}

        distributions = importlib.metadata.packages_distributions()
        for distro in distributions:
            if str(__name__).startswith(distro):
                name = distributions[distro][0]
                metadata = importlib.metadata.metadata(distro).json
                if metadata.get("project_url"):
                    for url in metadata["project_url"]:
                        try:
                            url = url.split(",")
                            if url[0].lower() == "documentation":
                                documentation_link = url[1]
                            elif url[0].lower() == "repository":
                                repo_link = url[1]
                        except Exception as e:
                            logger.error(f"Failed to get plugin URLs: {e}")

                if metadata.get("description_content_type") == "text/markdown":
                    readme = mistune.html(metadata.get("description"))
                else:
                    readme = metadata.get("description")

        return render_template("index.html", plugin_name=name, metadata=metadata, readme=readme,
                               documentation_link=documentation_link, repo_link=repo_link)

    @staticmethod
    @blueprint.route("/config")
    def config():
        config = {}

        for key in dir(DefaultConfig):
            if key.isupper():
                config[key] = app.config.get(key)

        return jsonify(config)

    @staticmethod
    @blueprint.route("/config", methods=["POST"])
    def update_config():
        try:
            result = DefaultConfig.update_config(request.json)
            if result["success"]:
                return jsonify(result)
            else:
                return jsonify(result), 400
        except BaseException as e:
            logger.error("Failed to update config:" + str(e))
            logger.error(traceback.format_exc())
            return jsonify({"success": False, "error": str(e)}), 400
