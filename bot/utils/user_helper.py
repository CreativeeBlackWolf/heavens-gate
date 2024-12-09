import datetime
from typing import Optional, Union

from pydantic import ValidationError

from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.utils.ip_utils import check_ip_address


def get_client_by_id_or_ip(id_or_ip: Union[str, int]) -> tuple[Optional[Client], Optional[str]]:
    """Tries to get client by it's id or ip.
    Returns `(Client, None)` if the user was found, `(None, "error_message")` otherwise"""
    if check_ip_address(id_or_ip):
        client = ClientFactory.get_client(id_or_ip)
    else:
        try:
            client = ClientFactory(tg_id=id_or_ip).get_client()
        except ValidationError:
            client = None

    if client is None:
        return None, f"❌ Пользователь <code>{id_or_ip}</code> не найден."
    return client, None

def get_user_data_string(client: Client) -> str:
    """Returns human-readable data about User.
    Recommended to use `parse_mode="HTML"`."""
    peers = client.get_peers()
    peers_str = ""

    for peer in peers:
        peers_str += f"{peer.peer_name or peer.shared_ips}: {PeerStatusChoices.to_string(peer.peer_status)} ({peer.shared_ips}) "
        if peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
            timer = datetime.datetime.strftime(peer.peer_timer, "%H:%M")
            peers_str += f"(активен до {timer})"
        peers_str += "\n"

    expire_time = client.userdata.expire_time.strftime("%d %b %Y") if client.userdata.expire_time else "❌ Не оплачено"

    return f"""ℹ️ Информация об аккаунте:
ID: <code>{client.userdata.telegram_id}</code>
Текущий статус: {ClientStatusChoices.to_string(client.userdata.status)}
Оплачен до: {expire_time}

🛜 Пиры:
{peers_str or '❌ Нет пиров\n'}
📅 Дата регистрации: {client.userdata.registered_at.strftime("%d %b %Y в %H:%M")}
"""

def extend_users_usage_time(client: Client, time_to_add: datetime.timedelta) -> bool:
    now = datetime.datetime.now()

    if not isinstance(client.userdata.expire_time, datetime.datetime) or client.userdata.expire_time < now:
        client.userdata.expire_time = now

    client.set_expire_time(client.userdata.expire_time + time_to_add)

    return True
