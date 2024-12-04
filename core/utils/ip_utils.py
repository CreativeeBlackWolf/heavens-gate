import ipaddress
import queue
from typing import Union

from core.logs import core_logger


class IPQueue:
    def __init__(self, ip_list: list[str]):
        self._ip_queue = queue.Queue()
        for ip in ip_list:
            self._ip_queue.put(ip)

    def get_ip(self) -> str:
        """
        Retrieve an IP address from the queue.

        Returns:
            str: The next available IP address from the queue.

        Raises:
            Exception: If no IP addresses are available in the queue.
        """
        if self._ip_queue.empty():
            core_logger.critical("No IP addresses available!")
            raise Exception("No IP addresses available")
        return self._ip_queue.get()

    def release_ip(self, ip: str) -> None:
        """
        Releases the specified IP address back to the IP queue.

        Args:
            ip (str): The IP address to be released.
        """
        core_logger.info(f"Releasing IP: {ip}")
        self._ip_queue.put(ip)

    def count_available_addresses(self) -> int:
        """
        Count the number of available addresses in the IP queue.

        Returns:
            int: The number of available addresses.
        """
        return self._ip_queue.qsize()


def check_ip_address(ip_address: str) -> bool:
    """Checks if IP address is valid.

    Returns:
        bool: True if IP address is valid. False otherwise.
    """
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def generate_ip_addresses(basic_ip: str, mask: Union[str, int] = "32") -> list[str]:
    """
    Generates IP addresses based on the given one with mask.

    Args:
        basic_ip (str): The base IP address to generate the network from. Example: 192.168.1
        mask (Union[str, int]): The subnet mask to apply. Defaults to "32".

    Returns:
        list[str]: A list of generated IP addresses within the specified subnet.
    """
    return [str(ip) for ip in ipaddress.IPv4Network(f"{basic_ip}.0/{mask}")]

def get_ip_prefix(ip_address: str) -> str:
    return '.'.join(ip_address.split('.')[:3])
