from dataclasses import dataclass


@dataclass
class DefaultConfig:
    # Config options go here in all caps with the name of your plugin first
    # This file will be loaded first, followed by user overrides from config.yml
    OTS_PLUGIN_TEMPLATE_API_KEY = "my_api_key"
