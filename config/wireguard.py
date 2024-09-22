import os

from config.settings import Config
from core.db.db_works import ClientFactory

from core.wg.wg_work import make_wg_server_base, peer_to_str_wg_server
from core.wg.wg_work import disable_server, enable_server

cfg = Config('config.conf')
server_cfg = cfg.get_server_config()

#Rewrite old config/create a brand new one
def create_wg_server_config(path, config_base):
    with open(path, "w", encoding="utf-8") as wg_file:
            wg_file.write(config_base)

#Add peers into config
def update_wg_server_config(path, peer_data):
    with open(path, "a", encoding="utf-8") as wg_file:
            wg_file.write(peer_data)

#Create wireguard server config
def create_server_config(wg_server):
    create_wg_server_config(wg_server, make_wg_server_base(server_cfg.user_ip, server_cfg.endpoint_port, server_cfg.private_key))
    peer_list = (ClientFactory.select_peers())
    for peer in peer_list:
        #Here I need to check if this peer should be in active server config
        update_wg_server_config(wg_server, peer_to_str_wg_server(peer))

#Func for use once at the beginning of installation
def create_wg_server():
    wg_server = os.getcwd()+"/wghub.conf"
    create_server_config(wg_server)
    enable_server(wg_server)
    return wg_server

#Func for every change of Wireguard server
def recreate_wg_server(wg_server):
    if "error" not in disable_server(wg_server):
        create_server_config(wg_server)
        enable_server(wg_server)
        return wg_server
    else:
         return False
