# Bitcoin Send-All / Custom-Amount Transaction Tool

A Python script to build and sign Bitcoin transactions with flexible fee options and optional change outputs.
Supports both **Mainnet** and **Testnet**, and can pull dynamic fees from mempool.space or Slipstream by Mara.

---

## Features

* **Send-All**: Send your entire wallet balance (minus fee) in a single output
* **Custom Amount**: Send a specified amount (in satoshis) and receive the remainder back as change
* **Flexible Fees**:

  * Specify fee in **USD** (`--fee-usd`)
  * Specify fee rate in **sats/vByte** (`--fee-rate`)
  * **Auto-fetch** recommended fees from **mempool.space** or **Slipstream** (`--fee-source`)
* **Network Selection**: Choose between **Mainnet** (`bitcoin`) and **Testnet** (`testnet`)

---

## Installation

1. Ensure you have **Python 3.7+**
2. Install dependencies:

   ```bash
   pip install bitcoinlib requests
   ```

---

## Usage

```bash
python send.py <TARGET_ADDRESS> <PRIVATE_KEY> [options]
```

### Command-Line Options

| Option                               | Description                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------- |
| `--send-sats <N>`                    | Amount to send in satoshis. If omitted, sends all funds minus fee.              |
| `--fee-usd <X>`                      | Fee amount in USD (overrides `--fee-rate`).                                     |
| `--fee-rate <Y>`                     | Fee rate in sats per vByte (overrides `--fee-source`).                          |
| `--fee-source {mempool, slipstream}` | API to auto-fetch fee rate if `--fee-rate` not provided. Defaults to `mempool`. |
| `--network {testnet, bitcoin}`       | Network to use (`bitcoin`=Mainnet, `testnet`=Testnet). Defaults to Mainnet.     |

### Examples

* **Send All Minus Fee** (using mempool.space fee):

  ```bash
  python send.py 3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5 L1aW4aubDFB7yfras2S1mME7zGZSMC --fee-rate 60
  ```

* **Send Specific Amount + USD Fee**:

  ```bash
  python send.py 3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5 L1aW4aubDFB7yfras2S1mME7zGZSMC \
    --send-sats 50000 \
    --fee-usd 0.50
  ```

* **Auto-Fetch Slipstream Fee**:

  ```bash
  python send.py 3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5 L1aW4aubDFB7yfras2S1mME7zGZSMC \
    --fee-source slipstream
  ```

---

## Slipstream Workflow

Fees on Slipstream can change rapidly. Follow these steps to ensure your transaction is prioritized:

1. **Generate Raw Transaction**

   ```bash
   python send.py <TARGET_ADDRESS> <PRIVATE_KEY> --fee-source slipstream
   ```

2. **Submit to Slipstream Web UI**

   * Visit: [https://slipstream.mara.com/](https://slipstream.mara.com/)
   * Paste your raw transaction and review the current fee recommendation.

3. **Adjust if Necessary**

   * If Slipstream’s required fee has jumped (e.g. above \$100), either:

     * **Re-run** the script to regenerate a fresh raw transaction with the updated rate
     * **Manually** specify `--fee-usd` to set at least \~\$100 so Slipstream prioritizes your TX

---

## Donations

If you find this tool helpful, your support is greatly appreciated! 💖

* **Bitcoin**: [bc1qh33frsqg06pafhcaj8kzljau04shwwp3ujwl6h](https://www.blockchain.com/btc/address/bc1qh33frsqg06pafhcaj8kzljau04shwwp3ujwl6h)

---

## Notes

* When you use `--send-sats`, any leftover (change) is sent back to your own address as a second output.
* Omit `--send-sats` to send **all** available funds (minus fee) in a single output.
* Always verify your raw transaction in a block explorer or on Slipstream’s UI before broadcasting.

---

## License

This project is licensed under the MIT License.

