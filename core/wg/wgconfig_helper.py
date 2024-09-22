from config.loader import server_cfg
from core.db.model_serializer import ConnectionPeer


def get_peer_config_str(peer: ConnectionPeer) -> str:
    return f"""[Interface]
Address={peer.shared_ips}/24
DNS=1.1.1.1
PrivateKey={peer.private_key}

[Peer]
PublicKey={server_cfg.public_key}
PresharedKey={peer.preshared_key}
AllowedIPs=0.0.0.0/0
Endpoint={server_cfg.endpoint_ip}:{server_cfg.endpoint_port}
"""
