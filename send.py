import requests
from bitcoinlib.keys import Key
from bitcoinlib.transactions import Transaction, Input, Output
from bitcoinlib.services.services import Service

def get_btc_price_usd():
    """
    Fetch current BTC price in USD from CoinGecko API.
    Returns:
        float: BTC price in USD.
    """
    try:
        resp = requests.get(
            'https://api.coingecko.com/api/v3/simple/price',
            params={'ids': 'bitcoin', 'vs_currencies': 'usd'}
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data['bitcoin']['usd'])
    except Exception as e:
        raise RuntimeError(f"Error fetching BTC price: {e}")

def get_recommended_fee_rate(source: str = 'mempool'):
    """
    Fetch recommended fee rate in sat/vByte.
    Args:
        source (str): 'mempool' or 'slipstream'
    Returns:
        float: recommended sats per vByte
    """
    try:
        if source == 'slipstream':
            url = 'https://slipstream.mara.com/rest-api/getinfo'
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            return float(data.get('fee_rate'))
        else:
            url = 'https://mempool.space/api/v1/fees/recommended'
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            return float(data.get('fastestFee'))
    except Exception as e:
        raise RuntimeError(f"Error fetching fee rate from {source}: {e}")

def estimate_tx_size(num_inputs: int, num_outputs: int):
    """
    Roughly estimate P2PKH transaction size.
    Args:
        num_inputs (int): number of inputs
        num_outputs (int): number of outputs
    Returns:
        int: estimated size in vBytes
    """
    # 148 vBytes per input, 34 vBytes per output, plus 10 vBytes overhead
    return 148 * num_inputs + 34 * num_outputs + 10

def create_signed_transaction(
        target_address: str,
        private_key_hex: str,
        send_amount_sats: int = None,
        fee_usd: float = None,
        fee_rate: float = None,
        fee_source: str = 'mempool',
        network: str = 'bitcoin'
):
    """
    Create and sign a Bitcoin transaction sending either:
      - a specified amount (send_amount_sats) plus change back to sender, or
      - the entire balance minus fee if send_amount_sats is None.

    Fee can be specified in USD or sats/vByte, or fetched from a fee API.

    Args:
        target_address (str): recipient Bitcoin address.
        private_key_hex (str): sender's private key (WIF or hex).
        send_amount_sats (int, optional): amount to send in satoshis.
        fee_usd (float, optional): fee amount in USD.
        fee_rate (float, optional): fee rate in sats per vByte.
        fee_source (str): 'mempool' or 'slipstream' if fee_rate not provided.
        network (str): 'testnet' or 'bitcoin' (mainnet).

    Returns:
        dict: {
            'success': bool,
            'raw_tx': str or None,
            'details': dict or error message
        }
    """
    try:
        # 1. Import key and derive source address
        key = Key(private_key_hex, network=network)
        source_address = key.address()

        # 2. Fetch UTXOs
        service = Service(network=network)
        utxos = service.getutxos(source_address)
        if not utxos:
            return {'success': False, 'raw_tx': None, 'details': "No UTXOs found"}

        # 3. Sum balance and count inputs
        total_sats = sum(u['value'] for u in utxos)
        num_inputs = len(utxos)

        # 4. Determine fee rate if needed
        if fee_rate is None and fee_usd is None:
            fee_rate = get_recommended_fee_rate(fee_source)

        # 5. Estimate number of outputs
        #    if sending full balance: 1 output; otherwise 2 (recipient + change)
        num_outputs = 1 if send_amount_sats is None else 2

        # 6. Estimate tx size and compute fee_sats
        est_size = estimate_tx_size(num_inputs, num_outputs)
        if fee_usd is not None:
            price_usd = get_btc_price_usd()
            fee_sats = int((fee_usd / price_usd) * 1e8)
        else:
            fee_sats = int(fee_rate * est_size)

        # 7. Determine send_sats
        if send_amount_sats is None:
            send_sats = total_sats - fee_sats
        else:
            send_sats = send_amount_sats
            if total_sats < send_sats + fee_sats:
                bal_btc = total_sats / 1e8
                needed = (send_sats + fee_sats) / 1e8
                return {
                    'success': False, 'raw_tx': None,
                    'details': f"Insufficient funds: balance {bal_btc:.8f} BTC, need {needed:.8f} BTC"
                }

        # 8. Build inputs
        inputs = []
        acc = 0
        for u in utxos:
            inputs.append(
                Input(
                    u['txid'],
                    u['output_n'],
                    address=source_address,
                    sequence=0xFFFFFFFF
                )
            )
            acc += u['value']
            if acc >= (send_sats + fee_sats):
                break

        # 9. Build outputs: recipient + optional change
        outputs = [Output(send_sats, target_address)]
        change_sats = total_sats - send_sats - fee_sats
        if change_sats > 0:
            outputs.append(Output(change_sats, source_address))

        # 10. Create, sign, serialize
        tx = Transaction(inputs, outputs, network=network)
        tx.sign(key)
        raw_hex = tx.raw_hex()

        # 11. Prepare details
        details = {
            'source_address': source_address,
            'target_address': target_address,
            'total_balance_sats': total_sats,
            'send_sats': send_sats,
            'change_sats': change_sats,
            'fee_sats': fee_sats,
            'fee_rate': fee_rate,
            'fee_usd': (fee_sats / 1e8 * get_btc_price_usd()) if fee_usd is None else fee_usd,
            'estimated_size_vbytes': est_size,
            'tx_hex': raw_hex,
            'explorer_urls': {
                'source': f'https://www.blockchain.com/btc/address/{source_address}',
                'target': f'https://www.blockchain.com/btc/address/{target_address}'
            }
        }
        return {'success': True, 'raw_tx': raw_hex, 'details': details}

    except Exception as e:
        return {'success': False, 'raw_tx': None, 'details': f"Error creating transaction: {e}"}

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Create & sign a Bitcoin transaction with optional send amount and flexible fees.'
    )
    parser.add_argument('target', help='Recipient address')
    parser.add_argument('private_key', help='Your private key (WIF or hex)')
    parser.add_argument('--send-sats', type=int, default=None,
                        help='Amount to send in satoshis (defaults to all funds minus fee)')
    parser.add_argument('--fee-usd', type=float, default=None,
                        help='Fee amount in USD (overrides rate)')
    parser.add_argument('--fee-rate', type=float, default=None,
                        help='Fee rate in sats/vByte')
    parser.add_argument('--fee-source', choices=['mempool', 'slipstream'], default='mempool',
                        help='API to fetch fee rate if not provided')
    parser.add_argument('--network', choices=['testnet', 'bitcoin'], default='bitcoin',
                        help='Network to use (default: mainnet)')
    args = parser.parse_args()

    result = create_signed_transaction(
        target_address=args.target,
        private_key_hex=args.private_key,
        send_amount_sats=args.send_sats,
        fee_usd=args.fee_usd,
        fee_rate=args.fee_rate,
        fee_source=args.fee_source,
        network=args.network
    )

    if not result['success']:
        print(f"Error: {result['details']}")
    else:
        d = result['details']
        print("=== Transaction Preview ===")
        print(f"Source Address        : {d['source_address']}")
        print(f"Explorer Link (Source): {d['explorer_urls']['source']}")
        print(f"Target Address        : {d['target_address']}")
        print(f"Explorer Link (Target): {d['explorer_urls']['target']}")
        print(f"Total Balance         : {d['total_balance_sats']/1e8:.8f} BTC")
        print(f"Send Amount           : {d['send_sats']} sats ({d['send_sats']/1e8:.8f} BTC)")
        if d['change_sats'] > 0:
            print(f"Change Amount         : {d['change_sats']} sats ({d['change_sats']/1e8:.8f} BTC)")
        print(f"Estimated Size        : {d['estimated_size_vbytes']} vBytes")
        print(f"Fee                   : {d['fee_sats']} sats (~${d['fee_usd']:.2f})")
        print("\nRaw Transaction Hex:")
        print(d['tx_hex'])
