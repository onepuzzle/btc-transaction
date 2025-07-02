#!/usr/bin/env python3
import sys
import json
import argparse
import requests

from bitcoinlib.keys import Key, Address
from bitcoinlib.transactions import Transaction, Input, Output
from bitcoinlib.services.services import Service

# ─── Configuration / Constants ────────────────────────────────────────────────

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
MEMPOOL_FEES_URL = "https://mempool.space/api/v1/fees/recommended"
SLIPSTREAM_URL = "https://slipstream.mara.com/rest-api/getinfo"

# ─── Helpers ───────────────────────────────────────────────────────────────────

def get_btc_price_usd() -> float:
    """Fetch current BTC price in USD from CoinGecko."""
    resp = requests.get(COINGECKO_URL, params={"ids": "bitcoin", "vs_currencies": "usd"}, timeout=10)
    resp.raise_for_status()
    return float(resp.json()["bitcoin"]["usd"])

def get_recommended_fee_rate(source: str = "mempool") -> float:
    """Fetch recommended fee rate (sats/vByte) from chosen API."""
    if source == "slipstream":
        resp = requests.get(SLIPSTREAM_URL, timeout=10)
        resp.raise_for_status()
        return float(resp.json().get("fee_rate"))
    resp = requests.get(MEMPOOL_FEES_URL, timeout=10)
    resp.raise_for_status()
    return float(resp.json().get("fastestFee"))

def estimate_tx_size(n_inputs: int, n_outputs: int) -> int:
    """Estimate P2PKH tx size: 148 vB per input + 34 vB per output + 10 vB overhead."""
    return 148 * n_inputs + 34 * n_outputs + 10

def fetch_utxos(address: str, network: str) -> list[dict]:
    """Retrieve UTXOs for a given address via bitcoinlib Service."""
    svc = Service(network=network)
    utxos = svc.getutxos(address)
    if not utxos:
        sys.exit(f"Error: No UTXOs found for {address}")
    return utxos

def build_transaction(
    source_address: str,
    utxos: list[dict],
    target_address: str,
    send_sats: int,
    fee_sats: int
) -> tuple[list[Input], list[Output], list[dict], int]:
    """
    Select minimal UTXOs to cover send + fee.
    Returns: inputs, outputs, used_utxos (original dicts), accumulator (sum of used utxos).
    """
    used_utxos = []
    inputs: list[Input] = []
    acc = 0

    for u in utxos:
        used_utxos.append({'txid': u['txid'], 'output_n': u['output_n'], 'value': u['value']})
        inputs.append(Input(
            u['txid'], u['output_n'],
            address=source_address,
            value=u['value'],
            sequence=0xFFFFFFFF
        ))
        acc += u['value']
        if acc >= send_sats + fee_sats:
            break

    outputs = [Output(send_sats, target_address)]
    change = acc - send_sats - fee_sats
    if change > 0:
        outputs.append(Output(change, source_address))

    return inputs, outputs, used_utxos, acc

def determine_witness_type(address: str) -> str:
    """
    Derive witness_type from an address via bitcoinlib:
      - 'legacy' for 1...
      - 'p2sh-segwit' for wrapped segwit
      - 'segwit' for native v0
      - 'p2tr' for taproot
    """
    addr_obj = Address.parse(address)
    return addr_obj.witness_type

def print_details(details: dict):
    """Nicely print the details dict you asked for."""
    print("=== Transaction Details ===")
    print(f"Source Address        : {details['source_address']}")
    print(f"Explorer Link (Source): {details['explorer_urls']['source']}")
    print(f"Target Address        : {details['target_address']}")
    print(f"Explorer Link (Target): {details['explorer_urls']['target']}")
    print(f"Total Balance         : {details['total_balance_sats']/1e8:.8f} BTC")
    print(f"Send Amount           : {details['send_sats']} sats ({details['send_sats']/1e8:.8f} BTC)")
    if details['change_sats'] > 0:
        print(f"Change Amount         : {details['change_sats']} sats ({details['change_sats']/1e8:.8f} BTC)")
    print(f"Estimated Size        : {details['estimated_size_vbytes']} vBytes")
    print(f"Fee Rate              : {details['fee_rate']} sats/vByte")
    print(f"Fee                   : {details['fee_sats']} sats (~${details['fee_usd']:.2f})")
    print("\nRaw Transaction Hex:")
    print(details['tx_hex'])

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Prepare or sign a Bitcoin transaction")
    p.add_argument("target_address", help="Recipient address")
    p.add_argument("key_or_address",
                   help="Private key (WIF/hex) to sign now, or wallet address to prepare unsigned TX")
    p.add_argument("--send-sats", type=int, default=None,
                   help="Amount to send (satoshis); default = all funds minus fee")
    p.add_argument("--fee-usd", type=float, default=None,
                   help="Flat fee in USD (overrides rate)")
    p.add_argument("--fee-rate", type=float, default=None,
                   help="Fee rate in sats/vByte (overrides API)")
    p.add_argument("--fee-source", choices=["mempool", "slipstream"], default="mempool",
                   help="API for fee rate if --fee-rate not set")
    p.add_argument("--network", choices=["bitcoin", "testnet"], default="bitcoin",
                   help="Network to use")
    args = p.parse_args()

    # 1. Determine source: private key → sign now; else just address → prepare only
    try:
        key = Key(args.key_or_address, network=args.network)
        source_address = key.address()
        is_key = True
    except Exception:
        source_address = args.key_or_address
        is_key = False

    # 2. Fetch UTXOs and compute total balance
    utxos = fetch_utxos(source_address, args.network)
    total_sats = sum(u["value"] for u in utxos)

    # 3. Fee calculation
    fee_rate = args.fee_rate or (get_recommended_fee_rate(args.fee_source) if args.fee_usd is None else None)
    est_size = estimate_tx_size(len(utxos), 2 if args.send_sats else 1)

    if args.fee_usd is not None:
        btc_price = get_btc_price_usd()
        fee_sats = int((args.fee_usd / btc_price) * 1e8)
        fee_usd = args.fee_usd
    else:
        fee_sats = int(fee_rate * est_size)
        fee_usd = (fee_sats / 1e8) * get_btc_price_usd()

    # 4. Determine send amount
    if args.send_sats is None:
        send_sats = total_sats - fee_sats
    else:
        send_sats = args.send_sats
        if send_sats + fee_sats > total_sats:
            sys.exit(f"Error: Insufficient funds. Balance={total_sats} sats, need={send_sats+fee_sats}")

    # 5. Build inputs, outputs
    inputs, outputs, used_utxos, acc = build_transaction(
        source_address, utxos, args.target_address, send_sats, fee_sats
    )
    change_sats = acc - send_sats - fee_sats
    actual_size = estimate_tx_size(len(inputs), len(outputs))

    # 6. Assemble details dict (without tx_hex yet)
    details = {
        'source_address': source_address,
        'target_address': args.target_address,
        'total_balance_sats': total_sats,
        'send_sats': send_sats,
        'change_sats': change_sats,
        'fee_sats': fee_sats,
        'fee_rate': fee_rate,
        'fee_usd': fee_usd,
        'estimated_size_vbytes': actual_size,
        'explorer_urls': {
            'source': f'https://www.blockchain.com/btc/address/{source_address}',
            'target': f'https://www.blockchain.com/btc/address/{args.target_address}'
        }
    }

    # 7a. If user passed a private key → sign immediately
    if is_key:
        witness_type = determine_witness_type(source_address)
        tx = Transaction(inputs, outputs,
                         network=args.network,
                         witness_type=witness_type)
        tx.sign(key)
        details['tx_hex'] = tx.raw_hex()
        print_details(details)
        return

    # 7b. Otherwise write unsigned files + interactive prompt
    tx = Transaction(inputs, outputs, network=args.network)
    unsigned_hex = tx.raw_hex()
    details['tx_hex'] = unsigned_hex

    # Save for offline signing
    with open("unsigned_tx.hex", "w") as f_hex, open("unsigned_data.json", "w") as f_json:
        f_hex.write(unsigned_hex)
        json.dump({**details, 'network': args.network, 'utxos': used_utxos}, f_json, indent=2)

    print("Unsigned transaction written to unsigned_tx.hex")
    print("UTXO & detail file written to unsigned_data.json")

    choice = input("Would you like to sign it now? [Y/n] ").strip().lower()
    if choice in ("y", "yes", ""):
        priv = input("Enter your private key (WIF or hex): ").strip()
        key2 = Key(priv, network=args.network)
        witness_type = determine_witness_type(source_address)
        tx2 = Transaction(inputs, outputs,
                          network=args.network,
                          witness_type=witness_type)
        tx2.sign(key2)
        details['tx_hex'] = tx2.raw_hex()
        print_details(details)
    else:
        print("You can sign later with sign.py and view details then.")

if __name__ == "__main__":
    main()
