from dataclasses import dataclass


@dataclass
class DefaultConfig:
    # Config options go here in all caps with the name of your plugin first
    # This file will be loaded first, followed by user overrides from config.yml
    OTS_AISSTREAM_PLUGIN_API_KEY = "your_api_key"
    OTS_AISSTREAM_PLUGIN_BBOX = [[[25.835302, -80.207729], [25.602700, -79.879297]], [[33.772292, -118.356139], [33.673490, -118.095731]] ]
    OTS_AISSTREAM_PLUGIN_COT_TYPE = "a-u-S-X-M"
    OTS_AISSTREAM_PLUGIN_COT_STALE_TIME = 3600  # CoT stale time in seconds
