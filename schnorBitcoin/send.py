from bitcoinlib.transactions import Transaction, Output
from bitcoinlib.keys import HDKey
import requests, json
from schnorr_lib import compute_aggregate_public_key
from bitcoinlib import encode_segwit_address
# from pycoin.encoding import bech32m_encode, convert_to_bech32m_data

# def encode_taproot_address(hrp, Q):
#     # Q is the 32-byte x-only public key
#     witness_program = Q
#     # Convert to 5-bit words
#     bech32m_data = convert_to_bech32m_data(witness_program)
#     # Prepend the witness version (1 for Taproot)
#     bech32m_data = [0x01] + bech32m_data
#     # Encode using Bech32m
#     address = bech32m_encode(hrp, bech32m_data)
#     return address


# Set network
NETWORK = 'testnet'  # Use 'bitcoin' for mainnet

users = json.load(open("users.json", "r"))["users"]

# Option1: Generate new keys
# key1 = HDKey(network=NETWORK)
# key2 = HDKey(network=NETWORK)
# key3 = HDKey(network=NETWORK)

# Display private keys (Keep them secure!)
# print("Private Key 1 (WIF):", key1.wif())
# print("Private Key 2 (WIF):", key2.wif())
# print("Private Key 3 (WIF):", key3.wif())

# Option2: Use existing keys, which is generated with schnorr signature scheme
key1 = users[0]
key2 = users[1]
key3 = users[2]

print("Private Key 1:", key1["privateKey"])
print("Private Key 2:", key2["privateKey"])
print("Private Key 3:", key3["privateKey"])

# Create a 3-of-3 multisig redeem script
public_keys = [key1["publicKey"], key2["publicKey"], key3["publicKey"]]

print(public_keys)

PK_agg = compute_aggregate_public_key(public_keys)
print("PK_agg: ", PK_agg)

# Assuming PK_agg is a Point object with x and y coordinates
x_only_pk = PK_agg.x.to_bytes(32, 'big')

# No tweak for key-only outputs (merkle_root = 0)
taproot_output_key = x_only_pk

# Testnet Taproot address
taproot_address = encode_segwit_address('tb', 1, taproot_output_key)

print("Taproot", taproot_address)

# Fetch UTXOs
def fetch_utxos(address):
    url = f'https://api.blockcypher.com/v1/btc/test3/addrs/{address}?unspentOnly=true&includeScript=true'
    response = requests.get(url)
    data = response.json()
    return data.get('txrefs', [])

utxos = fetch_utxos()

if not utxos:
    print("No UTXOs found for this address.")
    exit(1)

# Prepare inputs
inputs = []
total_input_value = 0

for utxo in utxos:
    txid = utxo['tx_hash']
    vout = utxo['tx_output_n']
    value = utxo['value']
    script_pub_key = utxo['script']
    total_input_value += value

    inputs.append({
        'txid': txid,
        'vout': vout,
        'value': value,
        'script_pub_key': script_pub_key,
        'redeem_script': redeem_script
    })

    break  # Use only one UTXO for this example

print(f"Total Input Value: {total_input_value} satoshis")

# Define outputs
destination_address = 'your_destination_address_here'  # Replace with an actual testnet address
amount_to_send = total_input_value - 1000  # Subtract fee

if amount_to_send <= 0:
    print("Insufficient funds to cover the transaction fee.")
    exit(1)

outputs = [
    Output(amount=amount_to_send, address=destination_address),
]

# Build transaction
tx = Transaction(network=NETWORK)

for tx_input in inputs:
    tx.add_input(prev_txid=tx_input['txid'],
                 output_n=tx_input['vout'],
                 script_type='multisig',
                 value=tx_input['value'],
                 script=tx_input['script_pub_key'],
                 redeemscript=tx_input['redeem_script'])

for output in outputs:
    tx.add_output(output)

tx.version = 2
tx.locktime = 0

# Sign transaction
tx.sign([key1], multisig_script=redeem_script)
tx.sign([key2], multisig_script=redeem_script)

if tx.is_signed:
    print("Transaction is fully signed.")
else:
    print("Transaction is not fully signed.")

# Get raw transaction hex
raw_tx_hex = tx.raw_hex()
print(f"Raw Transaction Hex: {raw_tx_hex}")

# Broadcast transaction
def broadcast_transaction(raw_tx_hex):
    url = 'https://api.blockcypher.com/v1/btc/test3/txs/push'
    payload = {'tx': raw_tx_hex}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

broadcast_result = broadcast_transaction(raw_tx_hex)
print(f"Broadcast Result: {broadcast_result}")
