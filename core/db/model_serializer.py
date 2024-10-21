from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from core.db.enums import ClientStatusChoices, PeerStatusChoices


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    name: str
    ip_address: Optional[str]
    active_time: Optional[datetime]
    status: ClientStatusChoices
    expire_time: Optional[datetime]
    registered_at: datetime

class ConnectionPeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    public_key: str
    private_key: str
    preshared_key: str
    shared_ips: str
    peer_name: Optional[str]
    peer_status: PeerStatusChoices
