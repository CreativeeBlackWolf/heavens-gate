import datetime

from peewee import (CharField, DateTimeField, ForeignKeyField, IntegerField,
                    Model)
from playhouse.sqlite_ext import AutoIncrementField, SqliteExtDatabase

from core.db.enums import ClientStatusChoices, PeerStatusChoices

db = SqliteExtDatabase(None, regexp_function=True)

class BaseModel(Model):
    class Meta:
        database = db


class UserModel(BaseModel):
    telegram_id = CharField(primary_key=True)
    name = CharField(default=None)
    ip_address = CharField(default=None, null=True)
    active_time = DateTimeField(default=None, null=True)
    status = IntegerField(
        default=ClientStatusChoices.STATUS_CREATED.value,
        choices=tuple(
            (status.value, status.name) for status in ClientStatusChoices
        )
    )
    expire_time = DateTimeField(default=None, null=True)
    registered_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "Users"

class ConnectionPeerModel(BaseModel):
    id = AutoIncrementField()
    user = ForeignKeyField(UserModel, backref="peer", on_delete="CASCADE")
    public_key = CharField()
    private_key = CharField()
    preshared_key = CharField()
    shared_ips = CharField()
    peer_name = CharField(default=None, null=True)
    peer_status = IntegerField(
        default=PeerStatusChoices.STATUS_DISCONNECTED.value,
        choices=tuple(
            (status.value, status.name) for status in PeerStatusChoices
        )
    )

    class Meta:
        table_name = "ConnectionPeers"


def init_db(path: str):
    db.init(database=path, pragmas={"foreign_keys": 1})
    db.connect()
    db.create_tables((UserModel, ConnectionPeerModel))
    return db
