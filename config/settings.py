import os
from configparser import ConfigParser
from typing import Type


class Config:
    cfg: ConfigParser

    def __init__(self, path_to_config: str):
        if not os.path.exists(path_to_config):
            raise FileNotFoundError(f"File was not found on path {path_to_config}")
        self.path = path_to_config

        self.cfg = ConfigParser(strict=False)
        self.cfg.read(path_to_config)

    def get_bot_config(self):
        return self.Bot(
            config_instance=self,
            token=self.cfg.get("TelegramBot", "token", fallback=None),
            admins=self.cfg.get("TelegramBot", "admins", fallback="")
        )

    def get_database_config(self):
        return self.Database(
            path=self.cfg.get("db", "path", fallback="db.sqlite")
        )

    def get_server_config(self):
        return self.Server(
            path=self.cfg.get("Server", "Path", fallback=os.getcwd() + "/wg0.conf"),
            user_ip=self.cfg.get("Server", "IP", fallback="127.0.0"),
            private_key=self.cfg.get("Server", "PrivateKey", fallback="@!ChAngEME!@"),
            public_key=self.cfg.get("Server", "PublicKey", fallback="@!ChAngEME!@"),
            endpoint_ip=self.cfg.get("Server", "EndpointIP", fallback="192.168.27.27"),
            endpoint_port=self.cfg.get("Server", "EndpointPort", fallback="10000")
        )

    def write_changes(self) -> bool:
        with open(self.path, "w", encoding="utf-8") as f:
            self.cfg.write(f)

        return True

    class Bot:
        def __init__(self, config_instance: Type["Config"], token: str, admins: str):
            self.token = token

            if not self.token:
                raise ValueError("Token MUST be specified in config file. For God's sake!")

            self.__admins = [int(admin_id) for admin_id in admins.split(",")] if admins else []
            self.__config_instance = config_instance

        @property
        def admins(self) -> list[int]:
            """List of user ids that have special rights"""
            return self.__admins

        def add_admin(self, admin_id: int) -> bool:
            if admin_id in self.admins:
                return False
            self.__admins.append(admin_id)
            self.__config_instance.cfg.set("TelegramBot", "admins", ",".join(str(i) for i in self.admins))
            self.__config_instance.write_changes()

            return True

    class Database:
        def __init__(self, path: str):
            self.path = path

    class Server:
        def __init__(self, path: str, user_ip: str, private_key: str, public_key: str, endpoint_ip: str, endpoint_port: str):
            self.path = path
            self.user_ip = user_ip
            self.private_key = private_key
            self.public_key = public_key
            self.endpoint_ip = endpoint_ip
            self.endpoint_port = endpoint_port
