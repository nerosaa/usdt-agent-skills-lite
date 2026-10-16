#!/usr/bin/env python3
"""
mcp-usdt-payment-check — minimal MCP stdio server (no paid APIs).

Tools:
  - check_usdt_payment: see if USDT arrived to an address on tron|bsc|ethereum|solana
  - validate_address: basic format check for an address on a chain

Uses free public endpoints only. Optional env:
  BSCSCAN_API_KEY, ETHERSCAN_API_KEY (improve rate limits; not required)
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

USDT = {
    "tron": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "bsc": "0x55d398326f99059fF775485246999027B3197955",
    "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "solana": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
}

DECIMALS = {"tron": 6, "bsc": 18, "ethereum": 6, "solana": 6}  # BSC USDT often 18

BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]+$")
EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def http_get(url: str, timeout: int = 25) -> Any:
    import time
    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; mcp-usdt-payment-check/1.0)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))
    raise last_err


def http_post_json(url: str, payload: dict, timeout: int = 25) -> Any:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "mcp-usdt-payment-check/1.0", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def validate_address(chain: str, address: str) -> Dict[str, Any]:
    chain = chain.lower().strip()
    address = address.strip()
    ok = False
    reason = ""
    if chain in ("bsc", "ethereum", "polygon"):
        ok = bool(EVM_RE.match(address))
        reason = "EVM address must be 0x + 40 hex chars" if not ok else "ok"
    elif chain == "tron":
        ok = address.startswith("T") and 33 <= len(address) <= 36 and bool(BASE58_RE.match(address))
        reason = "TRON address must start with T and be base58" if not ok else "ok"
    elif chain == "solana":
        ok = 32 <= len(address) <= 44 and bool(BASE58_RE.match(address))
        reason = "Solana address must be base58 length 32-44" if not ok else "ok"
    else:
        reason = f"unsupported chain: {chain}"
    return {"ok": ok, "chain": chain, "address": address, "reason": reason}


def _amt(raw: str, decimals: int) -> float:
    try:
        return int(raw) / (10 ** decimals)
    except Exception:
        return 0.0


def check_tron(address: str, min_amount: float, since_ms: Optional[int]) -> Dict[str, Any]:
    q = urllib.parse.urlencode(
        {
            "relatedAddress": address,
            "contract_address": USDT["tron"],
            "limit": 50,
            "start": 0,
            "filterTokenValue": 0,
        }
    )
    # Tronscan public endpoint
    url = f"https://apilist.tronscanapi.com/api/token_trc20/transfers?{q}"
    try:
        data = http_get(url)
    except Exception as e:
        # fallback older host
        url2 = f"https://api.tronscan.org/api/token_trc20/transfers?address={address}&contract_address={USDT['tron']}&limit=50"
        try:
            data = http_get(url2)
        except Exception as e2:
            return {"status": "error", "chain": "tron", "error": f"{e}; fallback: {e2}"}
    transfers = data.get("token_transfers") or data.get("data") or []
    matches = []
    for t in transfers:
        to_addr = t.get("to_address") or t.get("to") or ""
        if to_addr.lower() != address.lower() and to_addr != address:
            # relatedAddress query may include outgoing; keep inbound only
            if (t.get("to_address") or "") != address:
                continue
        quant = t.get("quant") or t.get("amount") or "0"
        amount = _amt(str(quant), DECIMALS["tron"])
        ts = t.get("block_ts") or t.get("block_timestamp") or 0
        if since_ms and ts and ts < since_ms:
            continue
        if amount + 1e-9 < min_amount:
            continue
        matches.append(
            {
                "tx": t.get("transaction_id") or t.get("transactionHash") or t.get("hash"),
                "amount_usdt": amount,
                "from": t.get("from_address") or t.get("from"),
                "timestamp_ms": ts,
            }
        )
    return _result("tron", address, min_amount, matches)


def check_evm(chain: str, address: str, min_amount: float, since_ms: Optional[int]) -> Dict[str, Any]:
    contract = USDT[chain]
    if chain == "bsc":
        host = "api.bscscan.com"
        key = os.environ.get("BSCSCAN_API_KEY", "")
        rpc = os.environ.get("BSC_RPC", "https://bsc.publicnode.com")
        decimals = 18
    else:
        host = "api.etherscan.io"
        key = os.environ.get("ETHERSCAN_API_KEY", "")
        rpc = os.environ.get("ETH_RPC", "https://ethereum.publicnode.com")
        decimals = 6
    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": contract,
        "address": address,
        "page": 1,
        "offset": 50,
        "sort": "desc",
    }
    if key:
        params["apikey"] = key
    url = f"https://{host}/api?{urllib.parse.urlencode(params)}"
    rows = None
    try:
        data = http_get(url)
        if isinstance(data, dict) and isinstance(data.get("result"), list):
            rows = data["result"]
        elif isinstance(data, dict) and data.get("status") == "0":
            rows = None  # fall through to RPC
    except Exception:
        rows = None

    if rows is not None:
        matches = []
        for tr in rows:
            if (tr.get("to") or "").lower() != address.lower():
                continue
            amount = _amt(tr.get("value") or "0", int(tr.get("tokenDecimal") or decimals))
            ts = int(tr.get("timeStamp") or 0) * 1000
            if since_ms and ts and ts < since_ms:
                continue
            if amount + 1e-9 < min_amount:
                continue
            matches.append(
                {
                    "tx": tr.get("hash"),
                    "amount_usdt": amount,
                    "from": tr.get("from"),
                    "timestamp_ms": ts,
                    "confirmations": tr.get("confirmations"),
                    "source": "explorer",
                }
            )
        return _result(chain, address, min_amount, matches)

    # RPC fallback: Transfer(address,address,uint256) topic
    transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    addr_topic = "0x" + address.lower().replace("0x", "").rjust(64, "0")
    try:
        latest = http_post_json(rpc, {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})
        latest_hex = latest.get("result", "0x0")
        latest_n = int(latest_hex, 16)
        from_block = hex(max(0, latest_n - 1500))
        logs = http_post_json(
            rpc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getLogs",
                "params": [{
                    "fromBlock": from_block,
                    "toBlock": "latest",
                    "address": contract,
                    "topics": [transfer_topic, None, addr_topic],
                }],
            },
        )
        if logs.get("error"):
            return {"status": "error", "chain": chain, "error": str(logs["error"])}
        matches = []
        for lg in logs.get("result") or []:
            raw = int(lg.get("data") or "0x0", 16)
            amount = raw / (10 ** decimals)
            if amount + 1e-9 < min_amount:
                continue
            frm = "0x" + (lg.get("topics") or ["", ""])[1][-40:]
            matches.append(
                {
                    "tx": lg.get("transactionHash"),
                    "amount_usdt": amount,
                    "from": frm,
                    "block": lg.get("blockNumber"),
                    "source": "rpc",
                }
            )
        return _result(chain, address, min_amount, matches)
    except Exception as e:
        return {"status": "error", "chain": chain, "error": f"explorer+rpc failed: {e}"}


def check_solana(address: str, min_amount: float, since_ms: Optional[int]) -> Dict[str, Any]:
    rpc = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
    try:
        sigs = http_post_json(
            rpc,
            {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [address, {"limit": 20}]},
        )
    except Exception as e:
        return {"status": "error", "chain": "solana", "error": str(e)}
    value = (sigs.get("result") or [])[:15]
    matches = []
    mint = USDT["solana"]
    for s in value:
        sig = s.get("signature")
        if not sig:
            continue
        try:
            tx = http_post_json(
                rpc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
                },
            )
        except Exception:
            continue
        result = tx.get("result") or {}
        meta = result.get("meta") or {}
        if meta.get("err"):
            continue
        block_time = (result.get("blockTime") or 0) * 1000
        if since_ms and block_time and block_time < since_ms:
            continue
        # scan token balance changes
        bals = meta.get("postTokenBalances") or []
        pre = { (b.get("accountIndex"), b.get("mint")): b for b in (meta.get("preTokenBalances") or []) }
        for b in bals:
            if b.get("mint") != mint:
                continue
            owner = (b.get("owner") or "")
            if owner and owner != address:
                continue
            post_amt = float(((b.get("uiTokenAmount") or {}).get("uiAmount")) or 0)
            prev = pre.get((b.get("accountIndex"), b.get("mint")))
            pre_amt = float((((prev or {}).get("uiTokenAmount") or {}).get("uiAmount")) or 0) if prev else 0.0
            delta = post_amt - pre_amt
            if delta + 1e-9 >= min_amount:
                matches.append(
                    {
                        "tx": sig,
                        "amount_usdt": delta,
                        "timestamp_ms": block_time,
                    }
                )
    return _result("solana", address, min_amount, matches)


def _result(chain: str, address: str, min_amount: float, matches: List[dict]) -> Dict[str, Any]:
    if matches:
        best = max(matches, key=lambda m: m.get("amount_usdt") or 0)
        return {
            "status": "paid",
            "chain": chain,
            "address": address,
            "min_amount": min_amount,
            "match_count": len(matches),
            "best": best,
            "matches": matches[:10],
        }
    return {
        "status": "not_paid",
        "chain": chain,
        "address": address,
        "min_amount": min_amount,
        "match_count": 0,
        "matches": [],
    }


def check_usdt_payment(chain: str, address: str, min_amount: float = 1.0, since_ms: Optional[int] = None) -> Dict[str, Any]:
    chain = chain.lower().strip()
    v = validate_address(chain, address)
    if not v["ok"]:
        return {"status": "error", "error": v["reason"], **v}
    if chain == "tron":
        return check_tron(address, float(min_amount), since_ms)
    if chain == "bsc":
        return check_evm("bsc", address, float(min_amount), since_ms)
    if chain in ("ethereum", "eth"):
        return check_evm("ethereum", address, float(min_amount), since_ms)
    if chain == "solana":
        return check_solana(address, float(min_amount), since_ms)
    return {"status": "error", "error": f"unsupported chain: {chain}"}


# ---- minimal MCP stdio (JSON-RPC style) ----

TOOLS = [
    {
        "name": "check_usdt_payment",
        "description": "Check whether USDT transfers to an address meet a minimum amount on tron, bsc, ethereum, or solana using free public APIs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "enum": ["tron", "bsc", "ethereum", "solana"]},
                "address": {"type": "string"},
                "min_amount": {"type": "number", "default": 1.0},
                "since_ms": {"type": "integer", "description": "Only count transfers at/after this unix ms timestamp"},
            },
            "required": ["chain", "address"],
        },
    },
    {
        "name": "validate_address",
        "description": "Basic format validation for a wallet address on tron, bsc, ethereum, polygon, or solana.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chain": {"type": "string"},
                "address": {"type": "string"},
            },
            "required": ["chain", "address"],
        },
    },
]


def handle(msg: dict) -> Optional[dict]:
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mcp-usdt-payment-check", "version": "1.0.0"},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            if name == "check_usdt_payment":
                result = check_usdt_payment(
                    args.get("chain", ""),
                    args.get("address", ""),
                    float(args.get("min_amount", 1.0)),
                    args.get("since_ms"),
                )
            elif name == "validate_address":
                result = validate_address(args.get("chain", ""), args.get("address", ""))
            else:
                result = {"error": f"unknown tool {name}"}
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}], "isError": False},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {"content": [{"type": "text", "text": json.dumps({"status": "error", "error": str(e)})}], "isError": True},
            }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main() -> None:
    # CLI smoke mode: python server.py check tron T... 10
    if len(sys.argv) >= 2 and sys.argv[1] in ("check", "validate"):
        if sys.argv[1] == "validate":
            print(json.dumps(validate_address(sys.argv[2], sys.argv[3]), indent=2))
            return
        chain, addr = sys.argv[2], sys.argv[3]
        amin = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        print(json.dumps(check_usdt_payment(chain, addr, amin), indent=2))
        return

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
