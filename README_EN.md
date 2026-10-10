<div align="center">

# 🍟 MaiMai Saver (麦麦省钱助手)

<img src="docs/assets/banner.svg" alt="MaiMai Saver" width="720" />

**Let AI get you McDonald's for less** — Agent Skill + standalone CLI in one repo

Built on McDonald's China official MCP Server (integration guide:
[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server)), covering
**35 official tools** across stores, menus, ordering, orders, coupons, points
mall, lottery and themed events.

**Core methodology**: before every order, a mandatory **4-step money-saving
check** — claim coupons → pick coupons → dual-price comparison → points
redemption evaluation. Every quote comes with a savings breakdown
(list price / discount / payable / saved).

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/Dependencies-None%20(stdlib)-green)
![Tests](https://img.shields.io/badge/Tests-43%20passed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-orange)
![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-purple)

[简体中文](README.md) · English

</div>

---

## Table of contents

- [Disclaimer](#disclaimer)
- [Features](#features)
- [Target users](#target-users)
- [Sample output](#sample-output)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
  - [Get an MCP Token](#get-an-mcp-token)
  - [Option A: connect via an MCP client](#option-a-connect-via-an-mcp-client)
  - [Option B: standalone CLI](#option-b-standalone-cli)
  - [Option C: install as an Agent Skill](#option-c-install-as-an-agent-skill)
  - [Option D: cross-channel comparison](#option-d-cross-channel-comparison)
- [Tool coverage](#tool-coverage-35-tools)
- [Use as an Agent Skill](#use-as-an-agent-skill)
- [Error handling](#error-handling)
- [Development and testing](#development-and-testing)
- [Contributing](#contributing)
- [License](#license)

## Disclaimer

- This is a **community open-source project with no affiliation with, nor
  endorsement from, McDonald's Corporation or its affiliates**.
- Using the McDonald's MCP service is subject to McDonald's China Terms of Use
  and the McDonald's MCP Service Rules; mainland China only (excluding Hong
  Kong, Macao and Taiwan), personal non-commercial use only.
- Provided "as is" without any guarantee of availability or accuracy. All
  savings figures come from actual tool responses; group-buy figures are
  local estimates from user-entered data.
- "McDonald's", "麦当劳", "麦乐送", "麦麦" and related marks belong to their
  respective owners; this project grants no trademark rights.

## Features

- **Savings-first**: built-in 4-step check and 11 saving strategies —
  coupon claiming, store-level coupon selection, dual-price comparison,
  points redemption evaluation, zero-cost combo swaps, campaign intel,
  free-draw reminders, group-meal promotions, survey-coupon recovery,
  card value assessment
- **Cross-channel comparison**: the bundled `deal_compare.py` engine lets
  users record McDonald's group-buy deals from Meituan/Douyin (manual entry,
  those platforms have no public APIs) and compare them against official
  prices with transparent rules and caveats
- **Zero dependencies**: the core MCP client uses only the Python 3.9+ standard library
- **Full MCP lifecycle**: `initialize` → `tools/list` → `tools/call`, automatic
  `Mcp-Session-Id` session handling, both `application/json` and
  `text/event-stream` responses
- **Production-grade error handling**:
  - 401 auth failures fail fast with guidance (no pointless retries)
  - 429 rate limits: exponential backoff with jitter honoring `Retry-After`
  - 5xx / network errors: automatic retries
  - JSON-RPC errors / `isError`: structured `McpToolError` with raw error data
- **Agent Skill ready**: `SKILL.md` ships triggers, workflows and conduct rules
  ("query before write / confirm before ordering / always run the savings check /
  never fabricate discounts / transparent comparisons") for WorkBuddy,
  Claude Code, Cursor, Codex and other agents
- **Secure by design**: token resolved from CLI arg / env var / file, never logged
- **Tested**: 43 unit tests covering SSE parsing, token resolution, comparison
  math and CLI exit codes

## Target users

| User | Typical usage |
|---|---|
| Frequent McDonald's customers | Automatic coupon claiming and best-price comparison on every order |
| Students / budget-conscious users | Combine group-buy deals with points redemption |
| Fitness / calorie-conscious users | Savings within a calorie budget via nutrition data |
| Group-buy app users | Manage McDonald's vouchers and compare against official deals |
| Office admins / group meals | Group-meal promotions and catering services |
| Agent / productivity tinkerers | Load the repo as an Agent Skill (WorkBuddy, Claude Code, ...) |

## Sample output

Cross-channel comparison report (`deal_compare.py compare`):

<div align="center">
<img src="docs/assets/compare-report.svg" alt="Cross-channel comparison report sample" width="720" />
</div>

<details>
<summary>View the text version</summary>

```text
========================================================================
麦麦省钱助手 · 全渠道比价报告（生成日期: 2026-10-10）
========================================================================
官方渠道方案：商品合计原价 ¥48.50，MCP 带券最优实付 ¥38.50（折扣率 79.4%）

团购券比价（按估算到手价升序，所有金额均为估算值）：
------------------------------------------------------------------------
  [81bb4c] meituan | 麦当劳满40减14代金券
      售价 ¥25.90 / 面值 ¥40.00 = 折扣率 64.8% | 同内容估算到手 ¥31.40 | 对比官方 +7.10 元
      限制: 仅堂食核销；限时段使用；2026-11-30前有效；每日限用1张

推荐决策（估算，实际以各平台页面与麦当劳官方渠道为准）：
  ✔ 建议使用团购券：麦当劳满40减14代金券（meituan）
    估算到手 ¥31.40，较官方渠道方案节省约 ¥7.10。
    注意：团购券通常不可叠加麦当劳官方优惠券，且需在适用门店/时段内核销；
    若本次订单内容未被该券覆盖，估算不成立，请以券详情页为准。
```

</details>

## Repository layout

```
maimai-saver/
├── SKILL.md                            # Agent Skill entry: methodology & rules
├── README.md                           # Project intro (Chinese)
├── README_EN.md                        # This file
├── CHANGELOG.md                        # Version history
├── LICENSE                             # MIT + third-party notice
├── CONTEST_DECLARATION.md              # Contest declaration (official, unmodified)
├── MCP_INTEGRATION.md                  # MCP integration: server/tools/flows/value
├── mcp-config.example.json             # Sanitized MCP config (env placeholder only)
├── workbuddy.md                        # WorkBuddy development session record
├── config/
│   └── mcp.example.json                # MCP client config example
├── scripts/
│   ├── mcd_client.py                   # MCP Streamable HTTP client (stdlib only)
│   ├── mcd.py                          # CLI: check / tools / schema / call
│   └── deal_compare.py                 # Cross-channel comparison engine
├── references/
│   ├── tools.md                        # Catalog of all 35 tools
│   ├── money-saving-strategies.md      # 11 saving strategies (core reference)
│   ├── agent-skill-installation.md     # WorkBuddy/Claude Code/Cursor/Codex install guide
│   ├── group-buy-comparison.md         # Cross-channel comparison methodology
│   ├── workflows.md                    # Business workflows
│   └── error-handling.md               # Errors, retries & troubleshooting
├── examples/
│   └── order-flow-example.md           # Full annotated ordering session
├── docs/assets/                        # README preview images (SVG)
├── tests/                              # pytest unit tests (43 cases)
└── .github/                            # CI + Issue/PR templates
```

## Quick start

### Get an MCP Token

1. Open <https://open.mcd.cn/mcp>, sign in (phone verification)
2. Console → Activate → accept the agreement → copy the MCP Token

### Option A: connect via an MCP client

Replace `${MCD_MCP_TOKEN}` in [`config/mcp.example.json`](config/mcp.example.json)
with your token and paste it into your client:

| Client | Where |
|---|---|
| WorkBuddy | `~/.workbuddy/mcp.json` |
| Cursor | Settings → Tools & MCP → mcp.json |
| Cherry Studio / Trae / VSCode / Kiro | their MCP settings (JSON import) |

### Option B: standalone CLI

```bash
git clone https://github.com/yuxinlaile/maimai-saver.git
cd maimai-saver

# Provide the token (choose one)
export MCD_MCP_TOKEN="your-token"          # env var (recommended)
echo "your-token" > ~/.mcd_mcp_token        # or a token file
# or pass --token "your-token" on every call

python scripts/mcd.py check                # verify token & connectivity
python scripts/mcd.py tools                # list all 35 tools
python scripts/mcd.py schema query-meals   # inspect a tool's input schema
python scripts/mcd.py call available-coupons   # try listing claimable coupons
```

**CLI exit codes**: `0` ok · `1` tool error · `2` auth · `3` rate-limited · `4` network

### Option C: install as an Agent Skill

The repo follows the open Agent Skills standard (SKILL.md) and installs as-is
into WorkBuddy, Claude Code, Cursor and OpenAI Codex:

| Platform | Project scope | User scope | Explicit invoke |
|---|---|---|---|
| WorkBuddy | `.workbuddy/skills/` | `~/.workbuddy/skills/` | auto-triggered |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | `/maimai-saver` |
| Cursor | `.cursor/skills/`, `.agents/skills/` | `~/.cursor/skills/`, `~/.agents/skills/` | `/maimai-saver` |
| OpenAI Codex | `.agents/skills/` | `~/.agents/skills/` | `$maimai-saver`, `/skills` |

```bash
git clone https://github.com/yuxinlaile/maimai-saver.git ~/.claude/skills/maimai-saver
# Cursor: ~/.cursor/skills/ · Codex: ~/.agents/skills/ · WorkBuddy: ~/.workbuddy/skills/
```

> The skill still needs the `mcd-mcp` MCP connection from
> [Option A](#option-a-connect-via-an-mcp-client) to call real tools.
> Per-platform details: [`references/agent-skill-installation.md`](references/agent-skill-installation.md).

### Option D: cross-channel comparison

```bash
# Record a McDonald's group-buy deal you found on Meituan/Douyin
python scripts/deal_compare.py add \
    --platform meituan --title "McDonald's ¥40-14 voucher" \
    --price 25.9 --face 40 --channel store --time limited \
    --valid-until 2026-11-30 --notes "1 per day"

# Compare against the official price (face 48.5 / best payable 38.5)
python scripts/deal_compare.py compare --mcd-face 48.5 --mcd-price 38.5
```

> Results are local estimates (group-buy platforms have no public APIs; data is
> user-entered). Methodology: [`references/group-buy-comparison.md`](references/group-buy-comparison.md).

## Tool coverage (35 tools)

| Domain | Tools |
|---|---|
| Nutrition | `list-nutrition-foods` |
| Addresses & stores | `delivery-query-addresses` `delivery-create-address` `delivery-query-stores` `query-nearby-stores` `query-meal-assistance` |
| Menu & pricing | `query-meals` `query-meal-detail` `calculate-price` `query-promotions` |
| Ordering & orders | `create-order` `cancel-order` `query-order` `order-list` `query-survey-coupon` |
| Coupons | `query-store-coupons` `available-coupons` `auto-bind-coupons` `query-my-coupons` |
| Points & mall | `query-my-account` `mall-points-products` `mall-product-detail` `mall-create-order` `mall-order-list` `mall-order-detail` |
| Points lottery | `query-lottery-info` `draw-lottery` `query-my-prizes` |
| Themed events | `query-party-city` `query-party-store` `query-partystore-date` `query-partystore-session` `party-order-create` |
| Utilities | `now-time-info` `campaign-calendar` |

Full catalog and usage notes: [`references/tools.md`](references/tools.md).

## Use as an Agent Skill

Clone the repo into your agent's skill directory and the agent will follow the
triggers and workflows defined in `SKILL.md`:

```bash
git clone https://github.com/yuxinlaile/maimai-saver.git ~/.workbuddy/skills/maimai-saver
```

Four conduct rules keep agent behavior safe and verifiable:

1. **Query before write** — gather full context before any mutating call.
2. **Confirm before ordering** — show key details and get explicit confirmation;
   payment links are passed through untouched, users pay themselves.
3. **Always run the savings check** — coupons → selection → dual-price
   comparison → points evaluation, with a savings breakdown.
4. **Never fabricate discounts** — every discount must come from actual tool
   responses such as `calculate-price`.

## Error handling

| Scenario | Behavior |
|---|---|
| HTTP 401 | Raises `AuthError` with re-apply guidance; no retry |
| HTTP 429 | Exponential backoff + jitter (default 3 retries), honors `Retry-After` |
| HTTP 5xx / network | Automatic retries (default 3) |
| Tool business errors | Raises `McpToolError` (raw data attached); verify params via `schema` |

See [`references/error-handling.md`](references/error-handling.md).

## Development and testing

```bash
# Syntax check (same as CI)
python -m py_compile scripts/mcd_client.py scripts/mcd.py scripts/deal_compare.py

# Unit tests (43 cases, no network required)
pip install pytest
python -m pytest tests/ -v
```

CI (`.github/workflows/ci.yml`) runs both on every push / PR.

## Contributing

Issues and PRs are welcome: workflow docs, translations, tool catalog updates
(McDonald's MCP iterates fast — the `tools` subcommand output is authoritative).

Before submitting: no real tokens anywhere; `python -m pytest tests/` passes.

## License

This project's code is released under the [MIT](LICENSE) license.

Note: running this project relies on the McDonald's China MCP service and the
upstream integration guide ([M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server));
using those services is additionally subject to McDonald's China Terms of Use,
the McDonald's MCP Service Rules and the upstream repository's usage
restrictions (personal, non-commercial use only).
