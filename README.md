# crypto

Cursor plugin that looks up, for a coin ticker, which networks Binance and OKX publish and the token contract address on each network when a public endpoint provides it. No login and no API keys.

## Tool

`get_coin_networks(symbol, exchange?)`

- `symbol`: ticker such as `USDT` or `PEPE`.
- `exchange`: optional `binance` or `okx`. Omit it to query both.

Each exchange entry includes:

| Field | Meaning |
| --- | --- |
| `network` | Exchange network code or name |
| `network_name` | Display name |
| `contract_address` | Token contract, or `null` when the public payload has none |
| `deposit_enabled` | Deposit open, or `null` when unpublished |
| `withdraw_enabled` | Withdrawal open, or `null` when unpublished |
| `withdraw_fee` | Withdrawal fee in the coin, when published |
| `withdraw_min` | Minimum withdrawal, when published |

## Endpoints that work without a key

Tested live with `curl` (no `OK-ACCESS-*` or Binance API-key headers).

### Binance: networks and contract addresses

`GET https://www.binance.com/bapi/capital/v1/public/capital/getNetworkCoinAll`

Unauthenticated website endpoint. Returns each coin's `networkList`, including `network`, `name`, `contractAddress`, `depositEnable`, `withdrawEnable`, `withdrawFee`, and `withdrawMin`. A query string such as `?coin=USDT` is ignored; the body is still the full list (~2 MB). The plugin caches it in memory for five minutes.

The official wallet route `GET https://api.binance.com/sapi/v1/capital/config/getall` is signed user data, not a keyless source. From this environment it also returned HTTP 451 (restricted location). The older paths `/bapi/capital/v1/public/capital/config/getall` and `/bapi/capital/v2/public/capital/config/getall` return HTTP 404.

### OKX: withdrawal networks, fees, and minimums only

`GET https://www.okx.com/v2/asset/withdraw/fee-amount-infos`

Unauthenticated. Each coin has parallel arrays `networkName`, `minFee`, and `minAmount`. There is no contract address and no deposit/withdraw enable flag. Example: PEPE is listed only on `Ethereum (ERC20)`; USDT is listed on many networks (Ethereum, Tron, Solana, and others).

**OKX does not publish contract addresses on a keyless endpoint.**

`GET https://www.okx.com/api/v5/asset/currencies` is the funding API that returns `chain`, `canDep`, `canWd`, `minWd`, `minFee`, and `ctAddr` (contract). Without `OK-ACCESS-KEY` it returns HTTP 401 `Request header OK-ACCESS-KEY can not be empty.` The same is true for `GET /api/v5/asset/deposit-withdraw-status`. This plugin does not call those routes and does not ask for keys.

Other public OKX routes that were checked and are not a substitute:

- `GET /api/v5/public/instruments` lists spot markets only. No networks or contracts.
- `GET /api/v5/asset/exchange-list` is a directory of other exchanges.
- `GET /priapi/v1/dx/market/v2/search` is OKX Web3 token search. It returns contract addresses for similarly named tokens on many chains, including unrelated contracts. It is not the OKX exchange deposit-network list, so it is not used.
- `GET /priapi/v3/growth/price/currency-detail` sometimes embeds a single explorer URL (PEPE's Ethereum contract appears in `blockBrowser`) and leaves `tokenContractAddress` empty. USDT's explorer URL has no contract. Not used as the network source.

## Run the local check

From the plugin root:

```bash
python3 scripts/test_coins.py
```

That queries USDT and PEPE on both exchanges and prints JSON. Python 3.11+ standard library only; nothing to install.

## MCP server

`mcp.json` starts `python3 ${CURSOR_PLUGIN_ROOT}/src/server.py` over stdio (Content-Length framed JSON-RPC). The server exposes `get_coin_networks`.

## Install / source

- Repository: https://github.com/manifoldor/crypto
- Requires Python 3.9+ (standard library only).

## 中文说明

`crypto` 插件：输入币种，查询币安和欧易支持的充提网络及各链合约地址，只用公开接口，无需登录或 API Key。
注意：欧易的公开接口不提供合约地址，欧易结果里的 `contract_address` 为空；币安可返回完整信息。

## License

MIT © 2026 Yishan Lin
