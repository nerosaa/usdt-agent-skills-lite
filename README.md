# USDT Agent Skills Lite (MIT)

Free starter pack: **2 agent skills** + a working **USDT payment-check MCP**, for freelancers paid in crypto.

Full commercial pack (6 skills + extras): **[Getly — Nero Tools](https://www.getly.store/store/nero-tools-mvb64f1s)**

## Included (lite)

| Item | Formats |
|------|---------|
| `usdt-invoice-request` | `SKILL.md` · Cursor `.mdc` · `AGENTS.md` |
| `wallet-address-safety` | `SKILL.md` · Cursor `.mdc` · `AGENTS.md` |
| `mcp-usdt-payment-check` | Python MCP/CLI (stdlib only) |

## Install

**Claude / Agent Skills:** copy `skills/<name>/` into your skills folder.

**Cursor:** copy `skills/<name>/cursor/*.mdc` into `.cursor/rules/`.

**Any agent:** paste `skills/<name>/prompts/AGENTS.md`.

**MCP:**
```bash
python3 mcp-usdt-payment-check/server.py check bsc 0xYourAddress 25
```

## Full pack unlocks

- `onchain-payment-verify`
- `crypto-freelancer-pricing`
- `stablecoin-bookkeeping`
- `bounty-hunting-workflow`
- Polished templates + workflow pack aligned with the [USDT Invoice Kit](https://www.getly.store/store/nero-tools-mvb64f1s)

Buy: https://www.getly.store/store/nero-tools-mvb64f1s

## License

MIT — see `LICENSE`.
