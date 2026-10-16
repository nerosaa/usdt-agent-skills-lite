# mcp-usdt-payment-check

Minimal **MCP** (Model Context Protocol) stdio server that checks whether **USDT** arrived at a wallet address. No paid APIs required.

## Tools

| Tool | Purpose |
|------|---------|
| `check_usdt_payment` | Look for inbound USDT on `tron` / `bsc` / `ethereum` / `solana` |
| `validate_address` | Basic format check before you publish an invoice address |

## Quick CLI test (no MCP client needed)

```bash
python3 server.py validate tron TYourAddressHere
python3 server.py check bsc 0xYourAddressHere 25
```

## MCP wiring (Claude Desktop / Cursor-compatible)

```json
{
  "mcpServers": {
    "usdt-payment-check": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp-usdt-payment-check/server.py"]
    }
  }
}
```

Optional env vars for higher explorer rate limits: `BSCSCAN_API_KEY`, `ETHERSCAN_API_KEY`, `SOLANA_RPC`.

## Safety

- Read-only. Never asks for private keys or seed phrases.
- Public chain data only. Not financial, tax, or legal advice.
- Explorer/RPC availability can change; treat `error` / `not_paid` carefully and re-check on the official explorer UI for large amounts.
