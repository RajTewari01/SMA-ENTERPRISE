from config.base import BaseConfig


class ProdConfig(BaseConfig):
    CONFIG_TYPE = "production"
    DEBUG = False