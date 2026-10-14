"""Public, unauthenticated coin-network lookups for Binance and OKX."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

BINANCE_NETWORKS_URL = (
    "https://www.binance.com/bapi/capital/v1/public/capital/getNetworkCoinAll"
)
OKX_WITHDRAW_FEES_URL = "https://www.okx.com/v2/asset/withdraw/fee-amount-infos"

OKX_LIMITATION = (
    "OKX has no keyless endpoint that returns deposit contract addresses. "
    "GET /api/v5/asset/currencies includes chain, canDep, canWd, minWd, minFee, "
    "and ctAddr, but it requires OK-ACCESS-KEY (HTTP 401 without it). "
    "This response uses the public website fee schedule "
    "GET /v2/asset/withdraw/fee-amount-infos, which lists withdrawal networks, "
    "minimums, and fees only. deposit_enabled, withdraw_enabled, and "
    "contract_address are null because that payload does not include them."
)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
CACHE_TTL_SECONDS = 300
_CACHE: dict[str, tuple[float, Any]] = {}


class LookupError(Exception):
    """A public endpoint failed or returned an unexpected payload."""


def _fetch_json(url: str) -> Any:
    now = time.time()
    cached = _CACHE.get(url)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise LookupError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LookupError(f"Request failed for {url}: {exc.reason}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise LookupError(f"Non-JSON response from {url}") from exc

    _CACHE[url] = (now, payload)
    return payload


def _blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _binance_networks(symbol: str) -> dict[str, Any]:
    payload = _fetch_json(BINANCE_NETWORKS_URL)
    if payload.get("code") != "000000" or not isinstance(payload.get("data"), list):
        raise LookupError(
            "Binance getNetworkCoinAll returned an unexpected payload: "
            f"code={payload.get('code')!r}"
        )

    coin = next(
        (item for item in payload["data"] if str(item.get("coin", "")).upper() == symbol),
        None,
    )
    result: dict[str, Any] = {
        "exchange": "binance",
        "source": BINANCE_NETWORKS_URL,
        "authenticated": False,
        "found": coin is not None,
        "name": None if coin is None else coin.get("name"),
        "limitations": None,
        "networks": [],
    }
    if coin is None:
        return result

    networks = []
    for item in coin.get("networkList") or []:
        networks.append(
            {
                "network": item.get("network"),
                "network_name": item.get("name") or item.get("networkDisplay"),
                "contract_address": _blank(item.get("contractAddress")),
                "deposit_enabled": item.get("depositEnable"),
                "withdraw_enabled": item.get("withdrawEnable"),
                "withdraw_fee": _blank(item.get("withdrawFee")),
                "withdraw_min": _blank(item.get("withdrawMin")),
            }
        )
    result["networks"] = networks
    return result


def _okx_networks(symbol: str) -> dict[str, Any]:
    payload = _fetch_json(OKX_WITHDRAW_FEES_URL)
    if payload.get("code") != 0 or not isinstance(payload.get("data"), list):
        raise LookupError(
            "OKX fee-amount-infos returned an unexpected payload: "
            f"code={payload.get('code')!r} msg={payload.get('msg')!r}"
        )

    coin = next(
        (
            item
            for item in payload["data"]
            if str(item.get("symbol", "")).upper() == symbol
        ),
        None,
    )
    result: dict[str, Any] = {
        "exchange": "okx",
        "source": OKX_WITHDRAW_FEES_URL,
        "authenticated": False,
        "found": coin is not None,
        "name": None if coin is None else coin.get("fullName"),
        "limitations": OKX_LIMITATION,
        "networks": [],
    }
    if coin is None:
        return result

    names = coin.get("networkName") or []
    fees = coin.get("minFee") or []
    minimums = coin.get("minAmount") or []
    networks = []
    for index, name in enumerate(names):
        fee = fees[index] if index < len(fees) else None
        minimum = minimums[index] if index < len(minimums) else None
        networks.append(
            {
                "network": name,
                "network_name": name,
                "contract_address": None,
                "deposit_enabled": None,
                "withdraw_enabled": None,
                "withdraw_fee": _blank(fee),
                "withdraw_min": _blank(minimum),
            }
        )
    result["networks"] = networks
    return result


_EXCHANGES = {
    "binance": _binance_networks,
    "okx": _okx_networks,
}


def get_coin_networks(symbol: str, exchange: str | None = None) -> dict[str, Any]:
    """Return public network rows for one coin.

    `exchange` is "binance", "okx", or omitted for both. Keys are never used.
    """
    ticker = (symbol or "").strip().upper()
    if not ticker:
        raise LookupError("symbol is required")

    selected = (exchange or "").strip().lower()
    if selected in ("", "all", "both"):
        names = ["binance", "okx"]
    elif selected in _EXCHANGES:
        names = [selected]
    else:
        raise LookupError("exchange must be binance, okx, or omitted")

    exchanges = []
    for name in names:
        try:
            exchanges.append(_EXCHANGES[name](ticker))
        except LookupError as exc:
            exchanges.append(
                {
                    "exchange": name,
                    "source": BINANCE_NETWORKS_URL
                    if name == "binance"
                    else OKX_WITHDRAW_FEES_URL,
                    "authenticated": False,
                    "found": False,
                    "name": None,
                    "limitations": str(exc),
                    "networks": [],
                    "error": str(exc),
                }
            )

    return {"symbol": ticker, "exchanges": exchanges}
