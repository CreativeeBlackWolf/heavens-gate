import subprocess


def generate_preshared_key(is_amnezia: bool = False):
    command = "wg" if not is_amnezia else "awg"
    return subprocess.getoutput(f"{command} genpsk")

def generate_private_key(is_amnezia: bool = False):
    command = "wg" if not is_amnezia else "awg"
    return subprocess.getoutput(f"{command} genkey")

def generate_public_key(private_key, is_amnezia: bool = False):
    command = "wg" if not is_amnezia else "awg"
    return subprocess.getoutput(f"echo {private_key} | {command} pubkey ")

if __name__ == "__main__":
    priv_key = generate_private_key()
    pub_key = generate_public_key(priv_key)
    presh_key = generate_preshared_key()
    print(f"Preshared key: {presh_key}")
    print(f"Private key: {priv_key}")
    print(f"Public key: {pub_key}")
