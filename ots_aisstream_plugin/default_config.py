import os
import traceback
from dataclasses import dataclass

import yaml
from flask import current_app as app
from opentakserver.extensions import logger


@dataclass
class DefaultConfig:
    # Config options go here in all caps with the name of your plugin first
    # This file will be loaded first, followed by user overrides from config.yml
    OTS_AISSTREAM_PLUGIN_API_KEY = "your_api_key"
    OTS_AISSTREAM_PLUGIN_BBOX = [[[25.835302, -80.207729], [25.602700, -79.879297]], [[33.772292, -118.356139], [33.673490, -118.095731]] ]
    OTS_AISSTREAM_PLUGIN_COT_TYPE = "a-u-S-X-M"
    OTS_AISSTREAM_PLUGIN_COT_STALE_TIME = 3600  # CoT stale time in seconds

    @staticmethod
    def validate(config:dict) -> dict[str, bool | str]:
        try:
            for key, value in config.items():
                if key not in DefaultConfig.__dict__.keys():
                    return {"success": False, "error": f"{key} is not a valid config key"}
                elif key == "OTS_AISSTREAM_PLUGIN_API_KEY":
                    if type(value) is not str or value.strip() == "":
                        return {"success": False, "error": f"{key} must be a non-empty string"}
                elif key == "OTS_AISSTREAM_PLUGIN_COT_TYPE":
                    if type(value) is not str or value.strip() == "" or not value.startswith("a-") or len(value.strip()) < 5:
                        return {"success": False, "error": f"{key} must start with a- and be at least 5 characters"}
                    elif value[2] not in "fhupansjk":
                        return {"success": False, "error": f"CoT type affiliation must be one of f, h, u, p, a, n, s, j, or k: {value[2]}"}
                    elif value[3] != "-" or not value[4].upper():
                        return {"success": False, "error": f"Invalid CoT type: {key}"}
                elif key == "OTS_AISSTREAM_PLUGIN_BBOX":
                    if type(value) is not list or len(value) == 0:
                        return {"success": False, "error": f"{key} must be a non-empty list"}
                elif key == "OTS_AISSTREAM_PLUGIN_COT_STALE_TIME":
                    if type(value) is not int or value < 0:
                        return {"success": False, "error": f"{key} must be a non-negative integer"}


            return {"success": True, "error": ""}

        except BaseException as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def change_config_setting(setting, value):
        try:
            with open(os.path.join(app.config.get("OTS_DATA_FOLDER"), "config.yml"), "r") as config_file:
                config = yaml.safe_load(config_file.read())

            config[setting] = value
            with open(os.path.join(app.config.get("OTS_DATA_FOLDER"), "config.yml"), "w") as config_file:
                yaml.safe_dump(config, config_file)

        except BaseException as e:
            logger.error("Failed to change setting {} to {} in config.yml: {}".format(setting, value, e))

    @staticmethod
    def update_config(config: dict) -> dict:
        try:
            valid = DefaultConfig.validate(config)
            if valid["success"]:
                for key, value in config.items():
                    app.config.update({key: value})
                    DefaultConfig.change_config_setting(key, value)
                return {"success": True}
            else:
                return valid
        except BaseException as e:
            logger.error(f"Failed to update config: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
