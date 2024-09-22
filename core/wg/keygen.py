import subprocess


def generate_preshared_key():
    return subprocess.getoutput("wg genpsk")

def generate_private_key():
    return subprocess.getoutput("wg genkey")

def generate_public_key(private_key):
    return subprocess.getoutput(f"echo {private_key} | wg pubkey ")

if __name__ == "__main__":
    priv_key = generate_private_key()
    pub_key = generate_public_key(priv_key)
    presh_key = generate_preshared_key()
    print(f"Here your Preshared key {presh_key}")
    print(f"Here your Private key {priv_key}")
    print(f"Here your Public key {pub_key}")
