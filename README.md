<div align="center">

# 🍟 麦麦省钱助手 (MaiMai Saver)

<img src="docs/assets/banner.svg" alt="麦麦省钱助手 MaiMai Saver" width="720" />

**让 AI 帮你用最少的钱吃麦当劳** —— Agent Skill + 独立 CLI 二合一

基于麦当劳中国官方 MCP Server（[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server) 集成指南）构建，
覆盖门店、菜单、点餐、订单、优惠券、积分商城、抽奖、主题活动等 **35 个官方工具**。

**核心方法论**：每次下单前自动执行 **领券 → 选券 → 比价 → 积分抵扣评估** 四步省钱检查，
每一次报价都附带省钱明细（原价 / 优惠 / 实付 / 节省比例）。

[![在线试算](https://img.shields.io/badge/%F0%9F%8C%90_在线试算-免登录-FFC72C?style=flat-square)](https://yuxinlaile.github.io/maimai-saver/demo.html)
[![Release](https://img.shields.io/badge/Release-v1.4.2-9a3412?style=flat-square)](https://github.com/yuxinlaile/maimai-saver/releases/tag/v1.4.2)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/Dependencies-None%20(stdlib)-green)
![Tests](https://img.shields.io/badge/Tests-98%20passed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-orange)
![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-purple)

简体中文 · [English](README_EN.md)

</div>

---

## 目录

- [项目简介](#项目简介)
- [免责声明](#免责声明)
- [核心功能](#核心功能)
- [工具能力总览](#工具能力总览)
- [技术栈](#技术栈)
- [目标用户](#目标用户)
- [效果预览](#效果预览)
- [目录结构](#目录结构)
- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
  - [申请 MCP Token](#申请-mcp-token)
  - [方式一：MCP 客户端直连](#方式一mcp-客户端直连)
  - [方式二：Agent Skill 安装](#方式二agent-skill-安装)
  - [方式三：CLI 独立使用](#方式三cli-独立使用)
  - [方式四：全渠道比价](#方式四全渠道比价)
- [运行与命令](#运行与命令)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [测试方式](#测试方式)
- [贡献指南](#贡献指南)
- [Star History](#star-history)
- [许可证](#许可证)

## 项目简介

麦麦省钱助手是一个以“省钱”为核心目标的麦当劳点餐 Agent Skill：它不是简单地
帮你下单，而是在**下单前强制执行省钱检查**——先把可领的券领完、再挑出当前
订单最优券、用 `calculate-price` 做无券/带券双价对比、最后评估积分兑换是否
更划算，然后把省钱明细（原价、优惠、实付、节省比例）一并展示给你确认。

项目同时提供：

- **Agent Skill**：一份 `SKILL.md` 遵循开放 Agent Skills 标准，可直接安装到
  WorkBuddy / Claude Code / Cursor / OpenAI Codex；
- **独立 CLI**：`scripts/mcd.py` 直连官方 MCP Server，无需任何 MCP 客户端，
  适合脚本与自动化场景；
- **全渠道比价引擎**：`scripts/deal_compare.py` 将美团/抖音等平台的麦当劳
  团购券（手动录入）与官方价格做同口径估算比价，输出“官方 vs 团购”决策建议。

## 免责声明

- 本项目为**社区开源项目，与麦当劳公司及其关联方无任何隶属、合作或背书关系**。
- 使用麦当劳 MCP 服务须遵守麦当劳中国《使用条款》及《麦当劳 MCP 服务规则》，
  仅限**中国大陆地区（不含港澳台）**、**个人非商业用途**。
- 本项目不对麦当劳 MCP 服务的可用性、准确性作任何保证，按"现状"提供；
  省钱明细均来自官方工具的实际返回值，不构成任何价格承诺。
- "McDonald's"、"麦当劳"、"麦乐送"、"麦麦"等名称与商标权利归属麦当劳公司，
  本项目不构成对上述商标的任何授权。

## 核心功能

- **省钱导向**：内置“省钱四步检查”与十一大省钱策略——领券前置、门店选券、
  无券/带券双价对比、积分抵扣评估、套餐零成本替换、活动情报、免费抽奖提醒、
  团餐满减、答卷奖券回收、卡类价值评估
- **全渠道比价**：美团/抖音团购券（手动录入，平台无公开 API）与官方渠道价格
  同口径估算对比，输出决策建议并提示叠加规则与限制条件
- **零依赖**：核心客户端仅使用 Python 3.9+ 标准库，克隆即用
- **完整 MCP 生命周期**：`initialize` → `tools/list` → `tools/call`，自动维护
  `Mcp-Session-Id` 会话，兼容 `application/json` 与 `text/event-stream` 响应
- **生产级错误处理**：401 快速失败不重试；429 指数退避 + 随机抖动自动重试并
  尊重 `Retry-After`；5xx/网络错误自动重试；工具层错误结构化（`McpToolError`）
- **Agent Skill 化**：`SKILL.md` 提供触发词、省钱工作流与调用规范
  （先查后改 / 下单必确认 / 省钱必检查 / 不虚构优惠 / 比价透明）
- **安全设计**：Token 支持环境变量/文件/参数三通道解析，绝不输出到日志
- **组合优化**：内置券组合优化器，枚举「无券直点/单券/凑单达标」候选方案，
  `--mcp` 模式经官方 calculate-price 逐方案真实计价，凑单以「不凑单」为基准并强制标注提示；
  多维约束支持预算/热量/蛋白质下限/钠上限（v1.5），违规方案排后如实标注
- **沉默成本体检**：临期券面值合计 + 历史订单消费画像（客单价/高频单品）+ 积分临期提醒，
  回答「你正在白扔多少钱」
- **测试保障**：98 个单元测试覆盖 SSE 解析、Token 解析、退避计算、
  比价折算决策、组合优化与 CLI 退出码

## 工具能力总览

| 业务域 | 工具 |
|---|---|
| 营养健康 | `list-nutrition-foods` |
| 地址与门店 | `delivery-query-addresses` `delivery-create-address` `delivery-query-stores` `query-nearby-stores` `query-meal-assistance` |
| 菜单与价格 | `query-meals` `query-meal-detail` `calculate-price` `query-promotions` |
| 点餐与订单 | `create-order` `cancel-order` `query-order` `order-list` `query-survey-coupon` |
| 优惠券 | `query-store-coupons` `available-coupons` `auto-bind-coupons` `query-my-coupons` |
| 积分与商城 | `query-my-account` `mall-points-products` `mall-product-detail` `mall-create-order` `mall-order-list` `mall-order-detail` |
| 积分抽奖 | `query-lottery-info` `draw-lottery` `query-my-prizes` |
| 主题活动 | `query-party-city` `query-party-store` `query-partystore-date` `query-partystore-session` `party-order-create` |
| 辅助 | `now-time-info` `campaign-calendar` |

完整说明与使用要点见 [`references/tools.md`](references/tools.md)。

## 技术栈

| 层面 | 技术 |
|---|---|
| 语言/运行时 | Python 3.9+（仅标准库：`urllib` / `json` / `argparse` / `datetime` / `uuid`） |
| 协议 | MCP Streamable HTTP + JSON-RPC 2.0（SSE 与 JSON 双格式响应） |
| 测试 | pytest（开发依赖，见 `requirements-dev.txt`） |
| CI | GitHub Actions（语法检查 + 单元测试，Python 3.9/3.11/3.13 矩阵） |
| 运行时第三方依赖 | **无** |

## 目标用户

| 用户 | 典型用法 |
|---|---|
| 麦当劳高频消费者 | 每次点餐自动完成"领券→选券→比价→积分评估"，长期降低单客成本 |
| 学生 / 预算敏感人群 | 结合团购券比价与积分兑换，用有限预算吃到更多 |
| 健身 / 控卡人群 | 结合营养数据做"热量预算内的省钱搭配" |
| 团购 App 用户 | 把手里囤的麦当劳团购券管起来，与官方券自动比较哪边更划算 |
| 企业行政 / 团餐组织者 | 团餐场景满减规则与助餐服务组合，降低团体订餐成本 |
| Agent / 效率工具玩家 | 将本仓库作为 Agent Skill（WorkBuddy / Claude Code 等）直接加载 |

## 效果预览

在线试算（免登录）：<https://yuxinlaile.github.io/maimai-saver/demo.html>

试算页内置 31 项菜单（7 大类，含早餐段）、9 张券、6 单美团/抖音团购示例与
跨渠道终局建议，并支持**一键导入真实菜单**——把 MCP `query-meals` 输出原样粘贴
即可全量替换示例数据，是官方菜单全量同步的正确姿势。

券组合优化（`optimizer.py` 实际输出）：

<div align="center">
<img src="docs/assets/optimizer-report.svg" alt="券组合优化输出示例" width="720" />
</div>

全渠道比价报告（`deal_compare.py compare` 实际输出）：

<div align="center">
<img src="docs/assets/compare-report.svg" alt="全渠道比价报告输出示例" width="720" />
</div>

<details>
<summary>查看文本版报告（节选）</summary>

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

## 目录结构

```
maimai-saver/
├── SKILL.md                            # Agent Skill 入口：省钱方法论与调用规范
├── README.md / README_EN.md            # 项目说明（中/英）
├── CHANGELOG.md                        # 版本变更记录
├── CONTRIBUTING.md                     # 贡献指南（参与方式/PR 流程/合规红线）
├── LICENSE                             # MIT + 第三方条款声明
├── CONTEST_DECLARATION.md              # 参赛声明（官方原文，未改动）
├── MCP_INTEGRATION.md                  # MCP 集成说明：Server/Tool/调用流程/业务价值
├── mcp-config.example.json             # 脱敏 MCP 配置（仅环境变量占位符）
├── workbuddy.md                        # WorkBuddy 对话上下文（参赛专项奖励核验）
├── requirements-dev.txt                # 开发/测试依赖（pytest）
├── config/
│   └── mcp.example.json                # MCP 客户端配置示例（占位符 Token）
├── install.ps1                         # Windows 一键安装脚本（备份旧版，不碰 Token）
├── scripts/
│   ├── mcd_client.py                   # MCP Streamable HTTP 客户端核心（纯标准库）
│   ├── mcd.py                          # CLI 入口：check / tools / schema / call / claim
│   ├── deal_compare.py                 # 全渠道比价引擎（美团/抖音券手动录入）
│   ├── optimizer.py                    # 券组合优化器（估算/--mcp 真实计价双模式）
│   └── silent_cost.py                  # 沉默成本体检（临期券/消费画像/积分）
├── references/
│   ├── tools.md                        # 35 个工具完整目录
│   ├── money-saving-strategies.md      # 十一大省钱策略详解（核心参考）
│   ├── agent-skill-installation.md     # WorkBuddy/Claude Code/Cursor/Codex 安装指南
│   ├── group-buy-comparison.md         # 外部团购比价方法论
│   ├── workflows.md                    # 业务工作流详解（含省钱检查前置流程）
│   └── error-handling.md               # 错误码、重试策略与排查指南
├── examples/
│   └── order-flow-example.md           # 完整省钱点餐示例会话
├── docs/
│   ├── demo.html                       # GitHub Pages 在线试算器（免登录）
│   └── assets/                         # README 预览图（SVG）
├── tests/                              # pytest 单元测试（98 个用例）
└── .github/                            # CI + Issue/PR 模板
```

## 环境要求

| 项目 | 要求 |
|---|---|
| Python | 3.9 或更高版本（仅标准库即可运行） |
| MCP Token | 在 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 免费申请（中国大陆手机号验证） |
| 网络 | 可访问 `https://mcp.mcd.cn`（麦当劳 MCP 服务，限中国大陆） |
| MCP 客户端 | 可选（WorkBuddy / Cursor / Claude Code / Codex 等，仅方式一、二需要） |
| 限流 | 每个 Token 每分钟最多 600 次请求 |

## 安装步骤

四种方式按需选择：方式一/二面向 Agent 对话场景，方式三适合脚本与自动化调试，
方式四为可选的省钱增强。所有方式都依赖下方申请的 MCP Token。

### 申请 MCP Token

1. 打开 <https://open.mcd.cn/mcp>，右上角【登录】（手机号验证）
2. 【控制台】→【激活】→ 同意服务协议 → 复制 MCP Token

### 方式一：MCP 客户端直连

将 [`config/mcp.example.json`](config/mcp.example.json) 中的 `${MCD_MCP_TOKEN}`
替换为实际 Token，粘贴到 MCP 客户端并启用 `mcd-mcp` 服务；各客户端的配置
位置见[配置说明](#配置说明)。接入后客户端自动暴露全部 35 个工具。

### 方式二：Agent Skill 安装

本技能遵循开放的 Agent Skills 标准（SKILL.md），同一仓库可直接安装到
WorkBuddy、Claude Code、Cursor、OpenAI Codex：

| 平台 | 项目级 | 用户级 | 显式调用 |
|---|---|---|---|
| WorkBuddy | `.workbuddy/skills/` | `~/.workbuddy/skills/` | 需求自动触发 |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | `/maimai-saver` |
| Cursor | `.cursor/skills/`、`.agents/skills/` | `~/.cursor/skills/`、`~/.agents/skills/` | `/maimai-saver` |
| OpenAI Codex | `.agents/skills/` | `~/.agents/skills/` | `$maimai-saver`、`/skills` |

```bash
git clone https://github.com/yuxinlaile/maimai-saver.git ~/.claude/skills/maimai-saver
# Cursor: ~/.cursor/skills/ · Codex: ~/.agents/skills/ · WorkBuddy: ~/.workbuddy/skills/
```

安装技能后仍需按[方式一](#方式一mcp-客户端直连)配置 `mcd-mcp` MCP 连接，
技能才能调用真实工具。各平台详细步骤见
[`references/agent-skill-installation.md`](references/agent-skill-installation.md)。

安装完成后 Agent 将依据 `SKILL.md` 的触发词与工作流自动调用，并遵守四条规范：

1. **先查后改**：所有写操作前必须先完成查询，上下文齐备。
2. **下单必确认**：任何下单/取消/兑换/抽奖操作前，必须向用户展示关键信息并获得
   明确确认；支付链接仅原样转交，由用户自行支付。
3. **省钱必检查**：下单前执行"领券→选券→比价→积分抵扣评估"四步检查，报价附带省钱明细。
4. **不虚构优惠**：每一笔优惠金额必须来自 `calculate-price` 等工具的实际返回值。

### 方式三：CLI 独立使用

```bash
git clone https://github.com/yuxinlaile/maimai-saver.git
cd maimai-saver

# 提供 Token（三选一）
export MCD_MCP_TOKEN="你的Token"          # 环境变量（推荐）
echo "你的Token" > ~/.mcd_mcp_token        # 或 Token 文件
# 或每次调用时 --token "你的Token"

python scripts/mcd.py check                # 验证 Token 与连通性
```

### 方式四：全渠道比价

```bash
# 把你在美团/抖音查到的麦当劳团购券录入本地券库
python scripts/deal_compare.py add \
    --platform meituan --title "麦当劳满40减14代金券" \
    --price 25.9 --face 40 --channel store --time limited \
    --valid-until 2026-11-30 --notes "每日限用1张"

# 与官方渠道（MCP 计算价格：原价 48.5 / 带券实付 38.5）比价
python scripts/deal_compare.py compare --mcd-face 48.5 --mcd-price 38.5
```

> 比价结果为本地估算（团购平台无公开 API，数据手动录入），方法论见
> [`references/group-buy-comparison.md`](references/group-buy-comparison.md)；
> 数据层支持 `MAIMAI_DEALS_PROVIDER` 环境变量接入外部数据源，为未来官方
> API 预留自动化接入点。

## 运行与命令

### mcd.py（官方 MCP 工具调用）

```bash
python scripts/mcd.py check                  # 检查 Token 有效性与服务器连通性
python scripts/mcd.py tools                  # 列出全部 35 个工具
python scripts/mcd.py schema query-meals     # 查看指定工具的入参 JSON Schema
python scripts/mcd.py call query-nearby-stores --arg address="北京市朝阳区xx路"   # 键值对传参
python scripts/mcd.py call query-meals --args '{"storeCode": "..."}' --raw      # 整体 JSON + 原始输出
python scripts/mcd.py claim                # 一键领取麦麦省可领券（展示清单→确认→领取）
```

**CLI 退出码**：`0` 成功 · `1` 工具错误 · `2` 鉴权失败 · `3` 限流 · `4` 网络错误

全局选项：`--token`、`--url`、`--timeout`（默认 30s）、`--retries`（默认 3）、
`--verbose`，子命令前后均可使用。

> **claim 的安全边界**：用户主动触发、单次执行，领取前必须展示清单并按 y 确认
> （`--yes` 仅供脚本场景跳过交互）；**不提供定时轮询与无人值守后台**——
> 这类自动化在风控侧等同于机器人行为，有 Token 封禁风险，本项目明确不做。

### deal_compare.py（全渠道比价）

```bash
python scripts/deal_compare.py add ...       # 录入团购券
python scripts/deal_compare.py list          # 列出券库（含有效期检查）
python scripts/deal_compare.py compare --mcd-face 48.5 --mcd-price 38.5
```

退出码：`0` 成功 · `1` 用法/数据错误 · `2` 券库为空。

### optimizer.py（券组合优化）

```bash
# 估算模式（本地计价，输出标注「未经验证」）
python scripts/optimizer.py plan --wants wants.json --menu menu.json --coupons coupons.json
# 真实计价模式（官方 calculate-price 逐方案核价，可作下单依据；需 --store-code）
python scripts/optimizer.py plan --wants wants.json --menu menu.json --coupons coupons.json \
    --mcp --store-code ST00123
python scripts/optimizer.py plan --wants wants.json --menu menu.json --coupons coupons.json \
    --budget 30 --max-kcal 800   # 可选：预算/热量约束，超支方案排后并标注
python scripts/optimizer.py plan --wants wants.json --menu menu.json --coupons coupons.json \
    --min-protein 20 --max-sodium 1500   # 可选：蛋白质下限/钠上限（v1.5，菜单含 protein/sodium 字段时生效）
python scripts/optimizer.py demo        # 离线演示
```

菜单条目可选 `kcal`（热量，来自 list-nutrition-foods）与 `contains`（套餐覆盖的单品
编码，用于生成"改点套餐"候选）；v1.5 起支持 `protein`（g）/`sodium`（mg）字段，
配合 `--min-protein` / `--max-sodium` 做营养约束——数据缺失的方案按不满足处理并
如实标注，绝不虚构达标。数据文件格式与各字段获取方式见脚本 docstring
与 SKILL.md 工作流 5。

### silent_cost.py（沉默成本体检）

```bash
python scripts/mcd.py call query-my-coupons --raw > coupons.json
python scripts/mcd.py call order-list --raw > orders.json
python scripts/mcd.py call query-my-account --raw > points.json
python scripts/silent_cost.py report --coupons coupons.json --orders orders.json --points points.json
python scripts/silent_cost.py demo      # 离线演示
```

## 配置说明

### 配置文件

| 文件 | 用途 |
|---|---|
| `config/mcp.example.json` | MCP 客户端接入模板（`${MCD_MCP_TOKEN}` 环境变量占位符） |
| `mcp-config.example.json` | 仓库根目录脱敏配置（参赛要求文件，仅环境变量占位符） |

### 环境变量

| 变量 | 说明 |
|---|---|
| `MCD_MCP_TOKEN` | MCP Token（优先级最高的提供方式） |
| `MCD_MCP_TOKEN_FILE` | Token 文件路径，默认 `~/.mcd_mcp_token` |
| `MCD_MCP_URL` | MCP Server 地址，默认 `https://mcp.mcd.cn` |
| `MAIMAI_DEALS_FILE` | 团购券库路径，默认 `~/.maimai_saver/deals.json` |
| `MAIMAI_DEALS_PROVIDER` | 外部数据源模块路径（实现 `load_deals()`），可选 |

### MCP 客户端配置位置

| 客户端 | 配置位置 |
|---|---|
| WorkBuddy | `~/.workbuddy/mcp.json`（或连接器管理页手动配置） |
| Cursor | 设置 → Tools & MCP → mcp.json |
| Cherry Studio / Trae / VSCode / Kiro | 各自 MCP 设置页（JSON 导入） |
| OpenAI Codex | `~/.codex/config.toml` 的 `[mcp_servers.mcd-mcp]` 段 |

### Token 安全要点

Token 仅通过环境变量、Token 文件或 `--token` 参数提供；绝不写入仓库文件、
绝不出现在日志与异常信息中；如不慎泄露，立即到 open.mcd.cn/mcp 重新申请。

## 常见问题

**Q1：调用报 401 鉴权失败？**
Token 无效、过期或未提供。检查 `MCD_MCP_TOKEN` / Token 文件 / `--token` 是否
正确，必要时到 <https://open.mcd.cn/mcp> 控制台重新申请。401 不会自动重试。

**Q2：频繁触发 429 限流？**
每个 Token 每分钟最多 600 次请求。CLI 已内置指数退避自动重试（尊重
Retry-After）；仍失败请降低调用频率，检查是否存在对 `query-meal-detail` 等
工具的循环逐个调用。

**Q3：`tools` 列表为空？**
先用 `python scripts/mcd.py check` 验证 Token 与连通性；确认 `--url` /
`MCD_MCP_URL` 未被改错。

**Q4：工具调用报参数错误（McpToolError）？**
不要猜参数名：执行 `python scripts/mcd.py schema <tool>` 查看权威入参；
编码类参数（storeCode、餐品编码、couponId 等）必须原样透传前序工具的返回值。

**Q5：网络错误或“无法解析的响应体”？**
网络错误会自动重试（默认 3 次）；持续出现请检查本地网络与代理，并按
[`references/error-handling.md`](references/error-handling.md) 的清单提 Issue
（请勿附 Token）。

**Q6：团购比价的数据从哪里来？**
美团/抖音无面向第三方的公开 API，券信息由你手动录入本地券库；比价结果为
估算值，实际以各平台页面为准。外部数据源可通过 `MAIMAI_DEALS_PROVIDER` 接入。

**Q7：支持哪些 Agent？**
WorkBuddy、Claude Code、Cursor、OpenAI Codex（同一 SKILL.md，无需修改），
安装目录见[方式二](#方式二agent-skill-安装)。

**Q8：如何确认技能安装成功？**
新开 Agent 会话输入显式调用命令（如 `/maimai-saver`）确认技能被识别；再执行
`python scripts/mcd.py check` 验证 MCP 连通性。

**Q9：optimizer 的估算模式和 --mcp 真实计价模式有什么区别？**
估算模式用菜单价格与券 threshold/discount 字段本地计算，输出标注「未经验证」，仅用于
快速比较；--mcp 模式调用官方 calculate-price 逐方案核价（含配送费与全部叠加规则），
结果才能作为下单依据。下单前仍须按 SKILL.md 规范用 calculate-price 复核并向你确认。

**Q10：麦当劳 MCP 的使用限制？**
仅限中国大陆地区（不含港澳台）、个人非商业用途；须遵守麦当劳中国《使用条款》
与《麦当劳 MCP 服务规则》，详见[免责声明](#免责声明)。

## 测试方式

```bash
# 语法检查（与 CI 一致）
python -m py_compile scripts/mcd_client.py scripts/mcd.py scripts/deal_compare.py scripts/optimizer.py scripts/silent_cost.py

# 安装开发依赖并运行单元测试（98 个用例，不发起网络请求）
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

CI（`.github/workflows/ci.yml`）在每次 push / PR 时自动执行语法检查与单元测试
（Python 3.9 / 3.11 / 3.13 矩阵）。

## 贡献指南

欢迎通过 Issue / PR 参与：工作流文档、中英文档校对、工具目录更新
（麦当劳 MCP 版本迭代较快，以 `tools` 子命令的实时结果为准）。
完整流程与规范见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

- Issue 模板：Bug 报告、功能建议（`.github/ISSUE_TEMPLATE/`）
- PR 模板：`.github/PULL_REQUEST_TEMPLATE.md`（含自检清单）
- 使用咨询 / 比价数据分享：[Discussions](https://github.com/yuxinlaile/maimai-saver/discussions)（已开启）

提交前请确认：

1. `python -m pytest tests/` 全部通过；
2. 未包含任何真实 Token、密码或个人凭证；
3. 涉及工具目录/工作流的变更已同步更新 `references/` 与 `SKILL.md`；
4. 用户可见变更已在 `CHANGELOG.md` 补充说明。

## Star History

觉得有用的话，点个 ⭐ 让更多麦门同仁看到：

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=yuxinlaile/maimai-saver&type=Date)](https://star-history.com/#yuxinlaile/maimai-saver&Date)

</div>

## 许可证

本项目代码以 [MIT](LICENSE) 许可证发布。

注意：本项目的运行依赖麦当劳中国 MCP 服务及其上游集成指南仓库
（[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server)），
相关服务的使用须另行遵守麦当劳中国的《使用条款》《麦当劳 MCP 服务规则》
及上游仓库的使用限制（个人非商业用途等）。
