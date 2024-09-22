import subprocess
from core.db.model_serializer import ConnectionPeer

def disable_server(path):
    return "error" in subprocess.getoutput(f"wg-quick down {path}")

def enable_server(path):
    return "error" in subprocess.getoutput(f"wg-quick up {path}")


def make_wg_server_base(ip, endpoint_port, private_key):
    return f"""[Interface]
Address = {ip}.1/24
ListenPort = {endpoint_port}
PrivateKey = {private_key}

"""

#def peer_for_wg_server_config(peer_name, public_key, preshared_key, shared_ips):
def peer_to_str_wg_server(peer: ConnectionPeer):
        return f"""
#{peer.peer_name}
[Peer]
PublicKey = {peer.public_key}
PresharedKey = {peer.preshared_key}
AllowedIPs = {peer.shared_ips}/32

"""