# Summary

Public, keyless lookups for Binance and OKX coin networks. Nothing was published or pushed.

## Endpoints that work

### Binance — networks, contracts, deposit/withdraw flags, fee, and minimum

`GET https://www.binance.com/bapi/capital/v1/public/capital/getNetworkCoinAll`

No API key. HTTP 200. Each coin has `networkList` with `network`, `name`, `contractAddress`, `depositEnable`, `withdrawEnable`, `withdrawFee`, and `withdrawMin`. `?coin=USDT` does not filter; the body is the full list. The plugin caches it for five minutes.

These do **not** work as a keyless contract source:

- `GET https://api.binance.com/sapi/v1/capital/config/getall` is signed user data. From this host it returned HTTP 451 (restricted location).
- `GET https://www.binance.com/bapi/capital/v1/public/capital/config/getall` and `/bapi/capital/v2/public/capital/config/getall` return HTTP 404.

### OKX — withdrawal networks, fee, and minimum only

`GET https://www.okx.com/v2/asset/withdraw/fee-amount-infos`

No API key. HTTP 200. Parallel arrays `networkName`, `minFee`, and `minAmount`. No contract address and no deposit/withdraw enable flag.

**There is no keyless OKX endpoint with contract addresses.**

- `GET https://www.okx.com/api/v5/asset/currencies` returns `chain`, `canDep`, `canWd`, `minWd`, `minFee`, and `ctAddr`, but without `OK-ACCESS-KEY` it returns HTTP 401 `Request header OK-ACCESS-KEY can not be empty.`
- `GET /api/v5/asset/deposit-withdraw-status` is the same 401.
- `GET /api/v5/public/instruments` is public and has no networks or contracts.
- `GET /priapi/v1/dx/market/v2/search` is Web3 token search. It returns many unrelated contracts that share a ticker, so it is not the OKX deposit-network list and is not used.

The tool still returns OKX networks, fees, and minimums, with `contract_address`, `deposit_enabled`, and `withdraw_enabled` set to `null`.

## How to run

From `/workspace/crypto-plugin` (Python 3.11+, standard library only):

```bash
python3 scripts/test_coins.py
```

That queries USDT and PEPE on both exchanges. Cursor loads the plugin from `.cursor-plugin/plugin.json` and `mcp.json`, which runs `python3 ${CURSOR_PLUGIN_ROOT}/src/server.py` and exposes `get_coin_networks(symbol, exchange?)`.

## Sample output

Live run of `scripts/test_coins.py` (fees change over time).

USDT: Binance 19 networks (18 with a contract; `STATEMINT` has none). OKX 16 networks, zero contracts.

```json
{
  "symbol": "USDT",
  "binance_examples": [
    {
      "network": "ETH",
      "network_name": "Ethereum (ERC20)",
      "contract_address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
      "deposit_enabled": true,
      "withdraw_enabled": true,
      "withdraw_fee": "0.5",
      "withdraw_min": "5"
    },
    {
      "network": "TRX",
      "network_name": "Tron (TRC20)",
      "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
      "deposit_enabled": true,
      "withdraw_enabled": true,
      "withdraw_fee": "1.5",
      "withdraw_min": "5"
    }
  ],
  "okx_examples": [
    {
      "network": "Ethereum (ERC20)",
      "contract_address": null,
      "deposit_enabled": null,
      "withdraw_enabled": null,
      "withdraw_fee": "0.37",
      "withdraw_min": "2"
    },
    {
      "network": "Tron (TRC20)",
      "contract_address": null,
      "deposit_enabled": null,
      "withdraw_enabled": null,
      "withdraw_fee": "1.5",
      "withdraw_min": "10"
    }
  ]
}
```

PEPE:

```json
{
  "symbol": "PEPE",
  "exchanges": [
    {
      "exchange": "binance",
      "found": true,
      "name": "Pepe",
      "networks": [
        {
          "network": "ETH",
          "network_name": "Ethereum (ERC20)",
          "contract_address": "0x6982508145454ce325ddbe47a25d4ec3d2311933",
          "deposit_enabled": true,
          "withdraw_enabled": true,
          "withdraw_fee": "239107",
          "withdraw_min": "478214"
        }
      ]
    },
    {
      "exchange": "okx",
      "found": true,
      "name": "Pepe",
      "networks": [
        {
          "network": "Ethereum (ERC20)",
          "network_name": "Ethereum (ERC20)",
          "contract_address": null,
          "deposit_enabled": null,
          "withdraw_enabled": null,
          "withdraw_fee": "155387.98",
          "withdraw_min": "655388"
        }
      ]
    }
  ]
}
```

A stdio MCP check (`initialize`, `tools/list`, `tools/call` for PEPE on OKX) returned the same OKX row.
