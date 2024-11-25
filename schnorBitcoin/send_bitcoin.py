#! /usr/bin/env python3
# STEP 3: Send the transaction

import requests, json
from bitcoinlib.transactions import Transaction
from schnorr_lib import schnorr_musig2_sign
import os

# Set network
NETWORK = 'testnet'  # Use 'bitcoin' for mainnet

# Check UTXO
def get_utxos(address):
    # Use Blockstream Testnet API to fetch UTXOs
    api_url = f"https://blockstream.info/testnet/api/address/{address}/utxo"
    response = requests.get(api_url)
    if response.status_code != 200:
        raise Exception(f"Error fetching UTXOs: {response.text}")
    utxos = response.json()
    return utxos

def check_utxos(utxos):
    for utxo in utxos:
        print(f"UTXO: {utxo['txid']}:{utxo['vout']} - Amount: {utxo['value']} satoshis")

# Function to construct transaction inputs
def construct_transaction_inputs(utxos, tx):
    total_input_amount = 0
    for utxo in utxos:
        txid = utxo['txid']
        vout = utxo['vout']
        amount = utxo['value']

        total_input_amount += amount
        tx.add_input(
            prev_txid=txid,
            output_n=vout,
            value=amount
        )
    return total_input_amount

# Function to estimate transaction size
def estimate_tx_size(num_inputs, num_outputs):
    # Estimations for Taproot transaction sizes
    input_size = 58  # Approximate size for a Taproot input (in vbytes)
    output_size = 43  # Size of a Taproot output (in vbytes)
    base_size = 10    # Base size of transaction
    total_size = base_size + (num_inputs * input_size) + (num_outputs * output_size)
    return total_size

# Function to construct transaction outputs
def construct_transaction_outputs(tx, total_input_amount, destination_address, amount_to_send, change_address, fee_rate=1):
    # Add output to the recipient
    tx.add_output(amount_to_send, destination_address)

    # Initially assume there will be a change output
    num_outputs = 2

    # Estimate transaction size to calculate fee
    num_inputs = len(tx.inputs)
    tx_size = estimate_tx_size(num_inputs, num_outputs)

    # Calculate the fee
    estimated_fee = tx_size * fee_rate

    # Calculate change amount
    change_amount = total_input_amount - amount_to_send - estimated_fee

    # Check if we have sufficient funds
    if change_amount < 0:
        raise Exception("Insufficient funds after fee calculation.")

    # Define dust threshold (minimum output amount)
    dust_threshold = 546  # In satoshis

    # Decide whether to add a change output
    if change_amount >= dust_threshold:
        # Add change output back to change_address
        tx.add_output(change_amount, change_address)
    else:
        # If change is less than dust threshold, add it to the fee
        estimated_fee += change_amount  # Adjust fee
        change_amount = 0
        num_outputs = 1  # No change output
        tx.outputs[0].value = amount_to_send  # Update recipient amount

    # Recalculate transaction size and fee
    tx_size = estimate_tx_size(num_inputs, num_outputs)
    estimated_fee = tx_size * fee_rate

    # Update the transaction fee
    tx.fee = estimated_fee

    return estimated_fee

# Function to read Taproot address from file
def read_taproot_address(file_path='taproot_address.txt'):
    try:
        with open(file_path, 'r') as file:
            line = file.readline().strip()
            if line.startswith("Taproot Address: "):
                address = line.split("Taproot Address: ", 1)[1]
                return address
            else:
                print(f"Error: Unexpected format in {file_path}")
                return None
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return None
    except IOError as e:
        print(f"Error reading {file_path}: {e}")
        return None

# Read the Taproot address from file
taproot_address = read_taproot_address()

if taproot_address:
    print(f"Taproot address: {taproot_address}")
    utxos = get_utxos(taproot_address)
    # After fetching UTXOs
    check_utxos(utxos)
else:
    print("Failed to read Taproot address. Exiting.")
    exit(1)

# Create a new transaction object
tx = Transaction(network=NETWORK)

# Construct transaction inputs
total_input_amount = construct_transaction_inputs(utxos, tx)

print(f"Total input amount: {total_input_amount} satoshis")
print(f"Number of inputs added: {len(tx.inputs)}")
# Set the default sequence if not already set
for inp in tx.inputs:
    if inp.sequence is None:  # Check if sequence is not set
        inp.sequence = 0xFFFFFFFF  # Set to default value

# Proceed to define transaction outputs and complete the transaction...

# Define transaction parameters
destination_address = 'mx1AtZz6a79qeeX1LpCZos1mNRftRLE7vj' 
amount_to_send = 50  # Amount to send in satoshis
change_address = taproot_address 
fee_rate = 1  # Fee rate in satoshis per byte

# Construct transaction outputs
estimated_fee = construct_transaction_outputs(
    tx,
    total_input_amount,
    destination_address,
    amount_to_send,
    change_address,
    fee_rate
)

print(f"Estimated transaction fee: {estimated_fee} satoshis")
print(f"Number of outputs: {len(tx.outputs)}")

# Calculate the transaction hash to be signed
tx_hash = tx.signature_hash()

def load_user_keys(filename="users.json"):
    # Read user keys from the file
    with open(filename, "r") as file:
        users_data = json.load(file)
        users = users_data["users"]

    # Extract private keys
    private_keys = [bytes.fromhex(user["privateKey"]) for user in users]

    print("Private keys loaded successfully")
    return users, private_keys

# Sign the transaction with Schnorr signatures
# Sign each input
users, private_keys = load_user_keys()
for i, inp in enumerate(tx.inputs):
    if i < len(private_keys):
        private_key = private_keys[i]
        signature = schnorr_musig2_sign(tx_hash, users)
        inp.script_type = 'p2tr'
        inp.signatures = [signature]

# Serialize the transaction
raw_tx = tx.raw()

print(f"Raw transaction (hex): {raw_tx.hex()}")

# Double check the transaction
# print(f"Number of inputs: {len(tx.inputs)}")
# print(f"Number of outputs: {len(tx.outputs)}")
# Print transaction details before sending
print("Transaction Details:")
print(f"Number of inputs: {len(tx.inputs)}")
for i, inp in enumerate(tx.inputs):
    print(f"Input {i}:")
    print(f"  Previous Transaction ID: {inp.prev_txid}")
    print(f"  Output Index: {inp.output_n}")
    print(f"  Value: {inp.value}")
    print(f"  Script Type: {inp.script_type}")
    print(f"  Signatures: {inp.signatures}")
    print(f"  Sequence: {inp.sequence}")

print(f"Number of outputs: {len(tx.outputs)}")
for j, out in enumerate(tx.outputs):
    print(f"Output {j}:")
    print(f"  Value: {out.value}")
    print(f"  Address: {out.address}")

print(f"Total input amount: {total_input_amount} satoshis")
print(f"Amount sent to destination: {amount_to_send} satoshis")
print(f"Fee: {estimated_fee} satoshis")

# Verify that inputs equal outputs plus fee
total_output = sum(output.value for output in tx.outputs)
if total_input_amount != total_output + estimated_fee:
    raise Exception("Transaction construction error: inputs do not equal outputs plus fee")

print("Transaction successfully constructed and verified.")
print("Ready for broadcasting.")

# Broadcast the transaction
def broadcast_transaction(raw_tx_hex):
    url = 'https://api.blockcypher.com/v1/btc/test3/txs/push'
    payload = {'tx': raw_tx_hex}
    
    try:
        response = requests.post(url, json=payload)
        
        # print(f"Status Code: {response.status_code}")
        # print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
        # print(f"Response Content: {response.text}")
        
        response.raise_for_status()
        
        if response.status_code == 201:
            tx_hash = response.json()['tx']['hash']
            print(f"Transaction broadcast successfully. Transaction ID: {tx_hash}")
            return tx_hash
        else:
            print(f"Unexpected response code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        # print(f"Failed to broadcast transaction. Error: {e}")
        # if hasattr(e, 'response') and e.response is not None:
        #     print(f"Error response content: {e.response.text}")
        return None

# After creating and signing the transaction
raw_tx_hex = raw_tx.hex()

# Broadcast the transaction
tx_hash = broadcast_transaction(raw_tx_hex)

if tx_hash:
    print(f"You can view the transaction at: https://live.blockcypher.com/btc-testnet/tx/{tx_hash}/")
# else:
#     print("Transaction broadcasting failed.")








