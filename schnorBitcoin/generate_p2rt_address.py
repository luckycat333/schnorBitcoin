CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'

# Constants for Bech32 and Bech32m
BECH32_CONST = 1
BECH32M_CONST = 0x2bc830a3

# Generator coefficients
GENERATOR = [
    0x3b6a57b2,
    0x26508e6d,
    0x1ea119fa,
    0x3d4233dd,
    0x2a1462b3,
]

def bech32_polymod(values):
    """Internal function that computes the Bech32 checksum."""
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            chk ^= GENERATOR[i] if ((top >> i) & 1) else 0
    return chk

def bech32_hrp_expand(hrp):
    """Expand the HRP for checksum computation."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def bech32_create_checksum(hrp, data, spec):
    """Compute the checksum values given HRP and data."""
    values = bech32_hrp_expand(hrp) + data
    const = BECH32M_CONST if spec == 'bech32m' else BECH32_CONST
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ const
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

def bech32_encode(hrp, data, spec='bech32'):
    """Compute a Bech32 or Bech32m string given HRP and data values."""
    checksum = bech32_create_checksum(hrp, data, spec)
    combined = data + checksum
    return hrp + '1' + ''.join([CHARSET[d] for d in combined])

def convertbits(data, frombits, tobits, pad=True):
    """General power-of-2 base conversion."""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret

# Main code to generate the P2TR address
def generate_p2tr_address(x_only_pub_key_hex, network='testnet'):
    # Convert hex public key to bytes
    x_only_pub_key_bytes = bytes.fromhex(x_only_pub_key_hex)
    
    # Ensure the public key is 32 bytes
    if len(x_only_pub_key_bytes) != 32:
        raise ValueError("Invalid public key length. Expected 32 bytes for x-only public key.")
    
    # Witness version and program
    witness_version = 1  # For Taproot
    witness_program = x_only_pub_key_bytes
    
    # Convert the witness program to 5-bit words
    data = [witness_version] + convertbits(witness_program, 8, 5)
    
    # Choose the correct HRP based on the network
    if network == 'mainnet':
        hrp = 'bc'
    elif network == 'testnet':
        hrp = 'tb'
    elif network == 'regtest':
        hrp = 'bcrt'
    else:
        raise ValueError("Invalid network. Use 'mainnet', 'testnet', or 'regtest'.")
    
    # Encode the address using Bech32m
    address = bech32_encode(hrp, data, spec='bech32m')
    return address
