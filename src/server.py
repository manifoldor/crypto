#!/usr/bin/env python3
"""Minimal stdio MCP server for the crypto plugin. Standard library only."""

from __future__ import annotations

import json
import sys
from typing import Any

from crypto_networks import LookupError, get_coin_networks

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "crypto", "version": "1.0.0"}

TOOL = {
    "name": "get_coin_networks",
    "description": (
        "Look up which chains Binance and OKX list for a coin, using public "
        "unauthenticated endpoints only. Returns network name, token contract "
        "address when the exchange publishes one, deposit/withdraw enabled "
        "flags, and withdraw fee and minimum when available. "
        "OKX's keyless fee schedule does not include contract addresses."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Coin ticker, for example USDT or PEPE.",
            },
            "exchange": {
                "type": "string",
                "enum": ["binance", "okx"],
                "description": "Optional. Omit to query both exchanges.",
            },
        },
        "required": ["symbol"],
        "additionalProperties": False,
    },
}


def _read_message() -> dict[str, Any] | None:
    header = sys.stdin.buffer.readline()
    if not header:
        return None
    if header.lower().startswith(b"content-length:"):
        length = int(header.split(b":", 1)[1].strip())
        while True:
            extra = sys.stdin.buffer.readline()
            if extra in (b"\r\n", b"\n", b""):
                break
        body = sys.stdin.buffer.read(length)
        return json.loads(body.decode("utf-8"))
    text = header.decode("utf-8").strip()
    if not text:
        return _read_message()
    return json.loads(text)


def _write_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _result(message_id: Any, result: dict[str, Any]) -> None:
    _write_message({"jsonrpc": "2.0", "id": message_id, "result": result})


def _error(message_id: Any, code: int, message: str) -> None:
    _write_message(
        {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {"code": code, "message": message},
        }
    )


def _tool_text(payload: dict[str, Any], is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ],
        "isError": is_error,
    }


def _call_tool(arguments: dict[str, Any] | None) -> dict[str, Any]:
    arguments = arguments or {}
    symbol = arguments.get("symbol")
    exchange = arguments.get("exchange")
    if not isinstance(symbol, str):
        return _tool_text({"error": "symbol is required"}, is_error=True)
    if exchange is not None and not isinstance(exchange, str):
        return _tool_text({"error": "exchange must be a string"}, is_error=True)
    try:
        return _tool_text(get_coin_networks(symbol, exchange))
    except LookupError as exc:
        return _tool_text({"error": str(exc)}, is_error=True)


def _handle(message: dict[str, Any]) -> None:
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params") or {}

    if method == "notifications/initialized" or message_id is None and method and method.startswith("notifications/"):
        return

    if method == "initialize":
        _result(
            message_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )
        return

    if method == "ping":
        _result(message_id, {})
        return

    if method == "tools/list":
        _result(message_id, {"tools": [TOOL]})
        return

    if method == "tools/call":
        if params.get("name") != TOOL["name"]:
            _error(message_id, -32602, f"Unknown tool: {params.get('name')}")
            return
        _result(message_id, _call_tool(params.get("arguments")))
        return

    if message_id is not None:
        _error(message_id, -32601, f"Method not found: {method}")


def main() -> None:
    while True:
        try:
            message = _read_message()
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"crypto mcp: failed to read message: {exc}", file=sys.stderr)
            return
        if message is None:
            return
        try:
            _handle(message)
        except BrokenPipeError:
            return
        except Exception as exc:
            message_id = message.get("id")
            print(f"crypto mcp: {exc}", file=sys.stderr)
            if message_id is not None:
                _error(message_id, -32603, str(exc))


if __name__ == "__main__":
    main()
