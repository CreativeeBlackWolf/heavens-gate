from config.loader import server_cfg
from core.db.model_serializer import ConnectionPeer


# TODO: add arguments for every server configuration paramenters since we are using configuration, which is bad
def get_peer_config_str(peer: ConnectionPeer, interface_args: dict = None) -> str:
    """
    Generates config string based on given ConnectionPeer.
    """
    interface_str = ""
    for k, v in interface_args.items():
        if k == "Junk":
            junk_vals = ["S1", "S2", "H1", "H2", "H3", "H4"]
            for ind, junk in enumerate(v.split(", ")):
                interface_str += f"{junk_vals[ind]} = {junk}\n"

        else:
            interface_str += f"{k} = {v}\n"

    # TODO: configurable PersistentKeepalive
    return f"""[Interface]
Address = {peer.shared_ips}/{server_cfg.user_ip_mask}
DNS = {server_cfg.dns_server}
PrivateKey = {peer.private_key}
{interface_str}

[Peer]
PublicKey = {server_cfg.public_key}
PresharedKey = {peer.preshared_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {server_cfg.endpoint_ip}:{server_cfg.endpoint_port}
PersistentKeepalive = 60
"""
