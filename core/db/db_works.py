from typing import Optional, Union

from multimethod import multimethod
from peewee import SQL, DoesNotExist
from pydantic import BaseModel, ConfigDict, PrivateAttr

from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.db.model_serializer import ConnectionPeer, User
from core.db.models import ConnectionPeerModel, UserModel
from core.wg.keygen import (generate_preshared_key, generate_private_key,
                            generate_public_key)


class Client(BaseModel):
    model_config = ConfigDict(ignored_types=(multimethod, ))

    userdata: User
    __model: UserModel = PrivateAttr(init=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "model" not in kwargs.keys():
            raise AttributeError("model attribute was not found in kwargs.")
        self.__model = kwargs["model"]

    def __update_client(self, **kwargs) -> bool:
        """Updates a user in database. Not ConnectionPeer

        Args:
            kwargs: DB fields
        Returns:
            True if operation was successfull. False otherwise.
        """
        return (self.__model.update(**kwargs)
                .where(UserModel.telegram_id == self.userdata.telegram_id)
                .execute()) == 1

    def __update_peer(self, peer_id: int, **kwargs) -> bool:
        """Updates a ConnectionPeer by peer id.

        Args:
            kwargs: DB fields
        Returns:
            True if operation was successfull. False otherwise.
        """
        return (ConnectionPeerModel.update(**kwargs)
                .where(ConnectionPeerModel.id == peer_id)
                .execute()) == 1

    def set_ip_address(self, ip_address: str) -> bool:
        self.userdata.ip_address = ip_address
        return self.__update_client(ip_address=ip_address)

    def set_status(self, status: ClientStatusChoices) -> bool:
        self.userdata.status = status
        return self.__update_client(status=status.value)

    def add_peer(self,
                 shared_ips: str,
                 public_key: Optional[str] = None,
                 private_key: Optional[str] = None,
                 preshared_key: Optional[str] = None,
                 peer_name: str = None) -> ConnectionPeer:
        """
        Adds peer to database. Automatically generates peer keys if they're not present in arguments.

        Returns `ConnectionPeer`.
        """
        private_peer_key = private_key or generate_private_key()
        public_peer_key = public_key or generate_public_key(private_peer_key)
        preshared_peer_key = preshared_key or generate_preshared_key()
        return ConnectionPeer.model_validate(ConnectionPeerModel.create(
            user=self.__model,
            public_key=public_peer_key,
            private_key=private_peer_key,
            preshared_key=preshared_peer_key,
            shared_ips=shared_ips,
            peer_name=peer_name
        ))

    def __get_peers(self, *criteria) -> list[ConnectionPeerModel]:
        """Private method for working with peers"""
        return list(ConnectionPeerModel.select()
                    .where(ConnectionPeerModel.user == self.__model, *criteria))

    def get_peers(self) -> list[ConnectionPeer]:
        """Get validated peers model(s)"""
        return [
            ConnectionPeer.model_validate(model)
            for model in self.__get_peers()
        ]

    def change_peer_name(self, peer_id: int, peer_name: str):
        self.__update_peer(peer_id, peer_name=peer_name)

    def set_peer_status(self, peer_id: int, peer_status: PeerStatusChoices):
        self.__update_peer(peer_id, peer_status=peer_status.value)

    def get_connected_peers(self) -> list[ConnectionPeer]:
        return [
            ConnectionPeer.model_validate(model)
            for model in self.__get_peers(ConnectionPeerModel.peer_status == PeerStatusChoices.STATUS_CONNECTED.value)
        ]

    @multimethod
    def delete_peer(self) -> bool:
        """Delete peers by `telegram_id`

        Returns:
            bool: True if successfull. False otherwise
        """
        return (ConnectionPeerModel.delete()
                .where(UserModel.telegram_id == self.userdata.telegram_id)
                .execute()) == 1

    @multimethod
    def delete_peer(self, ip_address: str) -> bool:
        """Delete single peer by `ip_address`

        Returns:
            bool: True if successfull. False otherwise
        """
        # ? weird flex but okay.
        formatted_ip = ip_address.replace(".", "\\.")
        return (ConnectionPeerModel.delete()
                .where(ConnectionPeerModel.shared_ips.regexp(
                    rf"(?:[, ]|^){formatted_ip}(?:[, ]|$)"
                ) & ConnectionPeerModel.user == self.__model)
                .execute()) == 1

class ClientFactory(BaseModel):
    model_config = ConfigDict(ignored_types=(multimethod, ))

    tg_id: int

    def get_or_create_client(self, name: str, **kwargs) -> Client:
        """Retrieves or creates a record of the user in the database.
        Use this method when you're unsure whether the user already exists in the database or not."""
        model = UserModel.get_or_create(telegram_id=self.tg_id, name=name, **kwargs)[0]
        return Client(model=model, userdata=User.model_validate(model))

    @multimethod
    def get_client(self) -> Optional[Client]:
        try:
            model = UserModel.get(UserModel.telegram_id == self.tg_id)
            return Client(model=model, userdata=User.model_validate(model))
        except DoesNotExist:
            return None

    @multimethod
    @staticmethod
    def get_client(ip_address: str) -> Optional[Client]:
        try:
            model = UserModel.get(UserModel.ip_address == ip_address)
            return Client(model=model, userdata=User.model_validate(model))
        except DoesNotExist:
            return None

    @staticmethod
    def select_clients() -> list[Client]:
        return [Client(model=i, userdata=User.model_validate(i)) for i in UserModel.select()]

    @staticmethod
    def select_peers() -> list[ConnectionPeer]:
        return [ConnectionPeer.model_validate(i) for i in ConnectionPeerModel.select()]

    @staticmethod
    def get_peer(ip_address: str) -> Optional[ConnectionPeer]:
        try:
            model = ConnectionPeerModel.get(ConnectionPeerModel.shared_ips == ip_address)
            return ConnectionPeer.model_validate(model)
        except DoesNotExist:
            return None

    @multimethod
    @staticmethod
    def delete_client(ip_address: str) -> bool:
        return UserModel.delete().where(UserModel.ip_address.contains(ip_address)).execute() == 1

    @multimethod
    def delete_client(self) -> bool:
        return UserModel.delete_by_id(self.tg_id)

    @staticmethod
    def count_clients() -> int:
        return UserModel.select().count()

    @staticmethod
    def get_latest_peer_id() -> int:
        try:
            return ConnectionPeerModel.select(ConnectionPeerModel.id).order_by(SQL("id").desc()).limit(1)[0].id
        except IndexError: #? assuming that there're no peers in DB
            return 1
