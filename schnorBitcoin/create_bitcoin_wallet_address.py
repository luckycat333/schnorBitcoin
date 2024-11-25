#! /usr/bin/env python3
# STEP 2: Create the bitcoin wallet address

from bitcoinlib.transactions import Transaction, Output, Input
from bitcoinlib.keys import HDKey, Key
from bitcoinlib.scripts import Script
from bitcoinlib.networks import Network
import requests, json
from bitcoinlib.encoding import to_bytes
from bitcoinlib.encoding import pubkeyhash_to_addr_bech32
import hashlib
import os

# Set network
NETWORK = 'testnet'  # Use 'bitcoin' for mainnet
network_info = Network(NETWORK)

# Add this constant at the top of your file, after the imports
SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

users = json.load(open("users.json", "r"))["users"]

# Load private keys
priv_keys = [user["privateKey"] for user in users]
# Convert hex public keys to bytes for each user
pub_keys = [bytes.fromhex(user["publicKey"]) for user in users]
print("Public Keys:", pub_keys)

# Convert keys to bitcoinlib Key objects
key_objs = [Key(import_key=priv_key, network=NETWORK) for priv_key in priv_keys]

# Create Tapscript for 3-of-3 multisig using OP_CHECKSIGADD
script = Script([
    pub_keys[0], b'\xac',  # OP_CHECKSIG
    pub_keys[1], b'\xba',  # OP_CHECKSIGADD
    pub_keys[2], b'\xba',  # OP_CHECKSIGADD
    3, b'\x9e'             # OP_NUMEQUAL
])

# Serialize the script
script_bytes = script.serialize()

# Compute TapLeaf hash
tapleaf_version = b'\xc0'  # 0xc0 for tapscript leaf version
leaf_hash = hashlib.sha256(tapleaf_version + script_bytes).digest()

# Choose an internal public key (could be any)
# For simplicity, we'll use the first public key (x-only)
internal_pubkey_bytes = key_objs[0].public_byte[1:]  # Remove the first byte (0x02 or 0x03)

# Compute the Taproot output key (tweaked public key)
tweak = int.from_bytes(leaf_hash, 'big')
internal_pubkey_int = int.from_bytes(internal_pubkey_bytes, 'big')
output_pubkey_int = (internal_pubkey_int + tweak) % SECP256K1_ORDER
output_pubkey_bytes = output_pubkey_int.to_bytes(32, 'big')

# Generate Taproot address
hrp = 'tb' if NETWORK == 'testnet' else 'bc'
taproot_address = pubkeyhash_to_addr_bech32(output_pubkey_bytes, prefix=hrp, witver=1)
# Save the Taproot address to a file
file_path = "taproot_address.txt"
with open(file_path, "w") as file:
    file.write(f"Taproot Address: {taproot_address}\n")

print(f"Taproot address saved to {os.path.abspath(file_path)}")

print("Taproot Address:", taproot_address)
