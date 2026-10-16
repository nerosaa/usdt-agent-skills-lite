# USDT Agent Skills Lite（开源精简版 · MIT）

免费起步包：包含 **2 个 Agent 技能** + 一个可运行的 **USDT 到账检查 MCP**，适合收加密货币/USDT 的自由职业者。

完整商业版（6 个技能 + 更多模板）：**[Getly 店铺](https://www.getly.store/store/nero-tools-mvb64f1s)**

## 精简版包含

| 内容 | 格式 |
|------|------|
| `usdt-invoice-request`（USDT 发票/付款请求） | `SKILL.md` · Cursor `.mdc` · `AGENTS.md` |
| `wallet-address-safety`（钱包地址安全检查） | `SKILL.md` · Cursor `.mdc` · `AGENTS.md` |
| `mcp-usdt-payment-check` | Python MCP/命令行（仅标准库） |

## 安装

**Claude / Agent Skills：** 把 `skills/<name>/` 拷到技能目录。

**Cursor：** 把 `skills/<name>/cursor/*.mdc` 拷到 `.cursor/rules/`。

**任意 Agent：** 粘贴 `skills/<name>/prompts/AGENTS.md`。

**MCP 到账检查：**
```bash
python3 mcp-usdt-payment-check/server.py check bsc 0x你的地址 25
```

## 完整版还包含

- 链上付款核验流程
- USDT 报价与套餐定价
- 稳定币简易记账
- 加密赏金工作流

购买：https://www.getly.store/store/nero-tools-mvb64f1s

## 许可证

MIT，见 `LICENSE`。
