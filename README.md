# Bitcoin Send-All / Custom-Amount Transaction Tool

A pair of Python scripts to build, sign and optionally broadcast Bitcoin transactions with flexible fee options and optional change outputs.  
Supports both **Mainnet** and **Testnet**, and can pull dynamic fees from mempool.space or Slipstream by Mara.

---

## Components

- **`send.py`**  
  - Build & sign (or prepare) a transaction in one step  
  - If you pass a private key, it signs immediately  
  - If you pass only an address, it writes:
    - `unsigned_tx.hex` — raw unsigned TX hex  
    - `unsigned_data.json` — metadata + UTXO values for offline signing  
  - Interactive prompt lets you sign immediately or later

- **`sign.py`**  
  - Take `unsigned_data.json` + your private key → rebuild inputs (with values) → sign → print signed TX hex  

---

## Features

- **Send-All**: send your entire balance (minus fee) in one output  
- **Custom Amount**: send a specified satoshi amount and return change to yourself  
- **Flexible Fees**:
  - **USD fee** (`--fee-usd`)  
  - **Rate** in sats/vByte (`--fee-rate`)  
  - **Auto-fetch** from **mempool.space** or **Slipstream** (`--fee-source`)  
- **Automatic Tx Type**: legacy vs P2SH-SegWit vs native SegWit vs Taproot is inferred from your source address  
- **Mainnet / Testnet** support (`--network`)

---

## Installation

1. Python 3.7+  
2. Install dependencies:

   ```bash
   pip install bitcoinlib requests

---

## Usage

### 1. `send.py`

```bash
python send.py <TARGET_ADDRESS> <KEY_OR_ADDRESS> [options]
```

* `<KEY_OR_ADDRESS>`

  * **WIF/hex** private key → build & sign immediately
  * **Wallet address**      → build unsigned and save files for later signing

#### Options

| Flag                                 | Description                                                   |
| ------------------------------------ | ------------------------------------------------------------- |
| `--send-sats <N>`                    | Amount (satoshis) to send. Omit to send *all* minus fee       |
| `--fee-usd <X>`                      | Flat fee in USD (overrides `--fee-rate`)                      |
| `--fee-rate <Y>`                     | Fee rate in sats/vByte (overrides `--fee-source`)             |
| `--fee-source {mempool, slipstream}` | Auto-fetch fee rate if no `--fee-rate`; defaults to `mempool` |
| `--network {bitcoin, testnet}`       | Default = `bitcoin` (Mainnet)                                 |

#### Examples

* **Send all minus fee** (auto-fee):

  ```bash
  python send.py bc1… L1a… --fee-source mempool
  ```

* **Custom amount + USD fee**:

  ```bash
  python send.py 3FZ… L1a… \
    --send-sats 50000 \
    --fee-usd 0.50
  ```

* **Prepare only (offline signing)**:

  ```bash
  python send.py bc1… 1A2…  # no private key passed
  ```

  This creates:

  * `unsigned_tx.hex`
  * `unsigned_data.json`

---

### 2. `sign.py`

```bash
python sign.py --data-file unsigned_data.json --private-key <YOUR_WIF>
```

* Reads `unsigned_data.json` (from `send.py`)
* Rebuilds all inputs with correct values & script type
* Signs and outputs **signed** TX hex

---

## Offline / Slipstream Workflow

1. **Prepare unsigned TX**

   ```bash
   python send.py <TARGET_ADDRESS> <YOUR_ADDRESS> --fee-source slipstream
   ```
2. **(Optional) Review raw TX**

   * Open `unsigned_tx.hex` in a block explorer
3. **Sign**

   ```bash
   python sign.py --data-file unsigned_data.json --private-key <YOUR_WIF>
   ```
4. **Broadcast**

   * Paste final hex into your preferred API/UI

---

## Notes

* Change outputs are sent back to your own address.
* The library infers the correct **witness\_type** (`legacy`, `p2sh-segwit`, `segwit`, `p2tr`) from your source address.
* Always double-check your raw hex on a block explorer before broadcasting.

---

## Donations

If you find this tool helpful, your support is greatly appreciated! 💖

**Bitcoin**: [1KrUmbGxbzHo8Xe12TUk4NLxzU2h8CiP2J](https://www.blockchain.com/btc/address/1KrUmbGxbzHo8Xe12TUk4NLxzU2h8CiP2J)

---

## License

This project is licensed under the MIT License.