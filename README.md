Create public/private key pairs by number of people
python3 create_keys.py -n 3

sign a message
python3 schnorr_sign.py --musig2 -m message

create taproot address 
python3 create_bitcoin_wallet_address.py

send bitcoin,boardcast
python3 send_bitcoin.py
