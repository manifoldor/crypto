#!/usr/bin/env python3
"""Query USDT and PEPE on Binance and OKX and print the public network data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crypto_networks import get_coin_networks  # noqa: E402


def main() -> None:
    report = [get_coin_networks(symbol) for symbol in ("USDT", "PEPE")]
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
