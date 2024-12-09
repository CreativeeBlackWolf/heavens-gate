import os
from configparser import ConfigParser
from getpass import getpass
from typing import Any, Union

import requests
from colorama import Fore, Style, init
from wgconfig import WGConfig

from core.utils.ip_utils import check_ip_address, get_ip_prefix
from core.wg.keygen import generate_private_key, generate_public_key

init(autoreset=True)

REQUIRE_INPUT_STR = Fore.YELLOW + "[ ! ]" + Style.RESET_ALL
SUCCESS_STR = Fore.GREEN + "[ + ]" + Style.RESET_ALL
FAIL_STR = Fore.RED + "[ - ]" + Style.RESET_ALL
YES_OR_NO_STR = Fore.CYAN + "[ ? ]" + Style.RESET_ALL

def make_config(path):
    # [TelegramBot]
    print(Style.BRIGHT + "--------- Bot Configuration ---------")
    tg_token = getpass(REQUIRE_INPUT_STR + " Telegram bot token (hidden): ")
    admins = input(REQUIRE_INPUT_STR + " Admin Telegram IDs with ',' separator: ")
    faq_url = input_with_default(REQUIRE_INPUT_STR + " FAQ URL (default: None): ", None)

    # [db]
    print(Style.BRIGHT + "--------- Database Configuration ---------")
    db_path = input_with_default(REQUIRE_INPUT_STR + " Database path (default: db.sqlite): ", "db.sqlite")

    # [core]
    print(Style.BRIGHT + "--------- Core Configuration ---------")
    peer_active_time = input_with_default(
        REQUIRE_INPUT_STR + " Peer active time in hours (default: 12): ", 12
    )
    connection_listen_timer = input_with_default(
        REQUIRE_INPUT_STR + " Connection listen timer in seconds (default: 120): ", 120
    )
    connection_update_timer = input_with_default(
        REQUIRE_INPUT_STR + " Connection update timer in seconds (default: 300): ", 300
    )
    connection_connected_only_listen_timer = input_with_default(
        REQUIRE_INPUT_STR + " Connection connected only listen timer in seconds (default: 60): ", 60
    )
    logs_path = input_with_default(REQUIRE_INPUT_STR + " Logs path (default: logs): ", "./logs")
    os.makedirs(logs_path, exist_ok=True)
    os.makedirs(os.path.join(logs_path, "bot"), exist_ok=True)
    os.makedirs(os.path.join(logs_path, "core"), exist_ok=True)
    print(SUCCESS_STR + " Logs path created")

    # [Server]
    print(Style.BRIGHT + "--------- Server Configuration ---------")

    server_config_data = {}
    path_to_wg_config = input_with_default(REQUIRE_INPUT_STR + " Enter path to WireGuard config (leave empty to enter values manually): ", None)

    is_amnezia = yes_or_no_input(YES_OR_NO_STR + " Are you using Amnezia WG? (Y/n (default)): ", False)
    manual_torture = False

    try:
        ip_api = requests.get('https://api.ipify.org', timeout=5)
        if ip_api.status_code != 200:
            raise ValueError
        server_config_data["EndpointIP"] = ip_api.content.decode("utf-8")
        print(SUCCESS_STR + " External IP fetched successfully")
    except (requests.exceptions.Timeout, ValueError):
        print(Fore.RED + "ipify is not accessible!" + Style.RESET_ALL)
        server_config_data["EndpointIP"] = input(REQUIRE_INPUT_STR + " Enter external ip manually: ")

    if path_to_wg_config is not None:
        if not os.path.exists(path_to_wg_config):
            print(FAIL_STR + f" WireGuard config was not found in {path_to_wg_config}")
            manual_torture = True
        else:
            server_config_data["Path"] = path_to_wg_config
            wg_config = WGConfig(path_to_wg_config)
            wg_config.read_file()

            interface_data = wg_config.get_interface()
            server_config_data["PrivateKey"] = interface_data.get("PrivateKey")
            server_config_data["PublicKey"] = generate_public_key(server_config_data["PrivateKey"], is_amnezia)
            server_ip = interface_data.get("Address")
            server_config_data["IP"] = get_ip_prefix(server_ip.split("/")[0])
            server_config_data["IPMask"] = server_ip.split("/")[1]
            server_config_data["EndpointPort"] = str(interface_data.get("ListenPort"))

            server_config_data["Junk"] = ", ".join([
                str(interface_data.get("S1", "")),
                str(interface_data.get("S2", "")),
                str(interface_data.get("H1", "")),
                str(interface_data.get("H2", "")),
                str(interface_data.get("H3", "")),
                str(interface_data.get("H4", "")),
            ])
    else:
        manual_torture = True

    if manual_torture:
        server_config_data["PrivateKey"] = generate_private_key(is_amnezia)
        server_config_data["PublicKey"] = generate_public_key(server_config_data["PrivateKey"], is_amnezia)
        server_config_data["IP"] = get_ip_range()
        server_config_data["IPMask"] = input_with_default(REQUIRE_INPUT_STR + " Enter the mask for IP address (default: 32): ", 32)
        server_config_data["EndpointPort"] = get_endpoint_port()

    # Put all data into config
    config = ConfigParser()
    config.optionxform = str
    config["TelegramBot"] = {
        "token": tg_token,
        "admins": admins,
        "faq_url": faq_url,
    }

    config["db"] = {
        "path": db_path
    }

    config["core"] = {
        "peer_active_time": peer_active_time,
        "connection_listen_timer": connection_listen_timer,
        "connection_update_timer": connection_update_timer,
        "connection_connected_only_listen_timer": connection_connected_only_listen_timer,
        "logs_path": logs_path
    }

    config["Server"] = server_config_data

    with open(path, 'w') as server_config:
        config.write(server_config)

    print(SUCCESS_STR + f" Config file created at {path}. Enjoy your ride!")

def get_ip_range() -> str:
    ip_range = yes_or_no_input(YES_OR_NO_STR + " Are you okay with '10.28.98.X' range for your IP addresses? Y/N (default: Y) -> ")
    if ip_range:
        return "10.28.98"
    ip_range = input(REQUIRE_INPUT_STR + " Your IP range ('0.0.0'): ")
    if check_ip_address(ip_range + ".1"):
        return ip_range
    print(FAIL_STR + " Invalid IP range")
    return get_ip_range()

def get_endpoint_port() -> str:
    endpoint_port = yes_or_no_input(YES_OR_NO_STR + " Are you okay with 54817 (recommended one) port for your Wireguard Service IP? Y/N (default: Y) -> ")
    if endpoint_port:
        return "54817"
    return input(REQUIRE_INPUT_STR + " Your endpoint port (check if it's free): ")

def input_with_default(prompt: str, default: Any) -> Union[str, Any]:
    value = input(prompt)
    return value if value else default

def yes_or_no_input(prompt: str, default: bool = True) -> bool:
    if (prompt.lower() in ["y", "yes"]) or (not prompt and default is True):
        return True
    return False

if __name__ == "__main__":
    make_config(os.getcwd() + "/config.conf")
