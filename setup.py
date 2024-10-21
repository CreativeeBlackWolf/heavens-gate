import os
from configparser import ConfigParser

from requests import get

from core.utils.check import check_ip_address
from core.wg.keygen import generate_private_key, generate_public_key


def make_config(path):
    # Create pair of crypto keys
    server_private_key = generate_private_key()
    server_public_key = generate_public_key(server_private_key)

    # Get external ip of your server
    external_ip = get('https://api.ipify.org').content.decode('utf8')
    tg_token = input("[ ! ] Telegram bot token: ")
    admins = input("[ ! ] Admin Telegram IDs with ',' separator: ")
    ip_range = get_ip_range()
    endpoint_port = get_endpoint_port()

    #Put all data into config
    config = ConfigParser()
    config.optionxform = str
    config["TelegramBot"] = {"token":f"{tg_token}", "admins": f"{admins}"}
    config["db"] = {"path": "db.sqlite"}
    config["Server"] = {
        "IP":f"{ip_range}",
        "PrivateKey": f"{server_private_key}",
        "PublicKey": f"{server_public_key}",
        "EndpointIP": f"{external_ip}",
        "EndpointPort":f"{endpoint_port}"
    }

    with open(path, 'w') as server_config:
        config.write(server_config)

def get_ip_range():
    ip_range = input("[ ? ] Are you okay with '10.28.98.X' range for your IP addresses? Y/N (default: Y) -> ")
    if ip_range.lower() in ["", "y", "yes"]:
        return "10.28.98"
    ip_range = input("[ ! ] Your IP range ('0.0.0'): ")
    if check_ip_address(ip_range + ".1"):
        return ip_range
    print("[ - ] Invalid IP range")
    return get_ip_range()

def get_endpoint_port():
    endpoint_port = input("[ ? ] Are you okay with 54817 (recommended one) port for your Wireguard Service IP? Y/N (default: Y) -> ")
    if endpoint_port.lower() in ["", "y", "yes"]:
        return "54817"
    return input("[ ! ] Your endpoint port (check if it's free): ")

if __name__ == "__main__":
    make_config(os.getcwd() + "/config.conf")
