from config.base import BaseConfig


class DevConfig(BaseConfig):
    CONFIG_TYPE = "development"
    DEBUG = True
