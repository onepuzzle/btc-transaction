#!/usr/bin/env python3
import sys
import json
import argparse
from bitcoinlib.keys import Key, Address
from bitcoinlib.transactions import Transaction, Input, Output

def main():
    parser = argparse.ArgumentParser(description="Sign a previously prepared Bitcoin transaction")
    parser.add_argument("--data-file", dest="datafile", default="unsigned_data.json",
                        help="Path to unsigned_data.json from send.py")
    parser.add_argument("--private-key", dest="wif", required=True,
                        help="Your private key (WIF or hex)")
    args = parser.parse_args()

    # 1. Load all utxos + details
    try:
        data = json.load(open(args.datafile))
    except Exception as e:
        print("Error reading data file:", e)
        sys.exit(1)

    # 2. Prepare key and addresses
    key = Key(args.wif, network=data['network'])
    source = data['source_address']
    target = data['target_address']
    send_sats = data['send_sats']
    change_sats = data['change_sats']

    # 3. Derive the correct witness_type from the source address
    addr_obj = Address.parse(source)
    witness_type = addr_obj.witness_type  # one of: 'legacy', 'p2sh-segwit', 'segwit', 'p2tr'

    # 4. Rebuild inputs/outputs with value fields
    inputs = []
    for u in data['utxos']:
        inputs.append(Input(
            u['txid'], u['output_n'],
            address=source,
            value=u['value'],
            sequence=0xFFFFFFFF
        ))
    outputs = [Output(send_sats, target)]
    if change_sats > 0:
        outputs.append(Output(change_sats, source))

    # 5. Create Transaction forcing the right witness_type, then sign
    tx = Transaction(
        inputs,
        outputs,
        network=data['network'],
        witness_type=witness_type
    )
    tx.sign(key)

    # 6. Output the fully signed TX hex
    print("=== Signed Transaction Hex ===")
    print(tx.raw_hex())

if __name__ == "__main__":
    main()
