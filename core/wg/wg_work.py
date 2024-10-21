import os
import subprocess
from typing import Callable, Union

import wgconfig

from core.db.model_serializer import ConnectionPeer


class WGHub:
    def __init__(self, path: str):
        self.path = path
        self.wghub = wgconfig.WGConfig(path)
        self.wghub.read_file()

    def apply_and_sync(func: Callable):
        def inner(self, peer: ConnectionPeer):
            func(self, peer)

            self.wghub.write_file()
            #! sync with server
        return inner

    @apply_and_sync
    def add_peer(self, peer: ConnectionPeer):
        self.wghub.add_peer(peer.public_key, f"# {peer.peer_name}")
        self.wghub.add_attr(peer.public_key, "PresharedKey", peer.preshared_key)
        self.wghub.add_attr(peer.public_key, "AllowedIPs", peer.shared_ips + "/32")

    @apply_and_sync
    def enable_peer(self, peer: ConnectionPeer):
        self.wghub.enable_peer(peer.public_key)

    @apply_and_sync
    def disable_peer(self, peer: ConnectionPeer):
        self.wghub.disable_peer(peer.public_key)

    @apply_and_sync
    def delete_peer(self, peer: ConnectionPeer):
        self.wghub.del_peer(peer.public_key)

def disable_server(path: str) -> bool:
    if not os.path.exists(path):
        return False
    """Returns True if server was disabled successfully"""
    return "error" in subprocess.getoutput(f"wg-quick down {path}")

def enable_server(path: str) -> bool:
    if not os.path.exists(path):
        return False
    """Returns True if server was enabled successfully"""
    return "error" in subprocess.getoutput(f"wg-quick up {path}")

def make_wg_server_base_str(ip: str, endpoint_port: Union[str, int], private_key: str) -> str:
    return f"""[Interface]
Address = {ip}.1/24
ListenPort = {endpoint_port}
PrivateKey = {private_key}

"""

def peer_to_str_wg_server(peer: ConnectionPeer) -> str:
    return f"""
# {peer.peer_name}
[Peer]
PublicKey = {peer.public_key}
PresharedKey = {peer.preshared_key}
AllowedIPs = {peer.shared_ips}/32

"""
