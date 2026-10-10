<div align="center">

# 🍟 麦麦省钱助手 (MaiMai Saver)

**让 AI 帮你用最少的钱吃麦当劳** —— Agent Skill + 独立 CLI 二合一

基于麦当劳中国官方 MCP Server（[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server) 集成指南）构建，
覆盖门店、菜单、点餐、订单、优惠券、积分商城、抽奖、主题活动等 **35 个官方工具**。

**核心方法论**：每次下单前自动执行 **领券 → 选券 → 比价 → 积分抵扣评估** 四步省钱检查，
每一次报价都附带省钱明细（原价 / 优惠 / 实付 / 节省比例）。

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/Dependencies-None%20(stdlib)-green)
![License](https://img.shields.io/badge/License-MIT-orange)
![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-purple)

简体中文 · [English](README_EN.md)*

</div>

> \* 英文版可按本文结构自行翻译贡献，欢迎 PR。

---

## ⚠️ 免责声明

- 本项目为**社区开源项目，与麦当劳公司及其关联方无任何隶属、合作或背书关系**。
- 使用麦当劳 MCP 服务须遵守麦当劳中国《使用条款》及《麦当劳 MCP 服务规则》，
  仅限**中国大陆地区（不含港澳台）**、**个人非商业用途**。
- 本项目不对麦当劳 MCP 服务的可用性、准确性作任何保证，按"现状"提供；
  省钱明细均来自官方工具的实际返回值，不构成任何价格承诺。
- "McDonald's"、"麦当劳"、"麦乐送"、"麦麦"等名称与商标权利归属麦当劳公司，
  本项目不构成对上述商标的任何授权。

## ✨ 功能特性

- **🎯 省钱导向**：内置"省钱四步检查"与十一大省钱策略——领券前置、
  门店选券、无券/带券双价对比、积分抵扣评估、套餐零成本替换、
  活动情报、免费抽奖提醒、团餐满减、答卷奖券回收、卡类价值评估
- **🔀 全渠道比价**：内置团购比价引擎 `deal_compare.py`，将美团/抖音等平台的
  麦当劳团购券（手动录入，无公开 API）与官方渠道价格做同口径估算比价，
  输出"官方 vs 团购"决策建议（含叠加规则与限制提示）
- **零依赖**：核心客户端仅使用 Python 3.9+ 标准库，克隆即用
- **完整 MCP 生命周期**：`initialize` → `tools/list` → `tools/call`，
  自动维护 `Mcp-Session-Id` 会话，兼容 `application/json` 与 `text/event-stream` 两种响应
- **生产级错误处理**：
  - 401 鉴权失败：快速失败并给出修复指引（不无谓重试）
  - 429 限流：指数退避 + 随机抖动自动重试，尊重 `Retry-After`
  - 5xx / 网络错误：自动重试
  - JSON-RPC error / `isError`：结构化异常（`McpToolError`）携带原始错误数据
- **Agent Skill 化**：`SKILL.md` 提供触发词、省钱工作流、
  "先查后改 / 下单必确认 / 省钱必检查 / 不虚构优惠 / 比价透明"调用规范，可直接被 WorkBuddy / Claude Code 等 Agent 加载
- **安全设计**：Token 支持环境变量/文件/参数三通道解析，绝不输出到日志

## 🎯 目标用户

| 用户 | 典型用法 |
|---|---|
| 麦当劳高频消费者 | 每次点餐自动完成"领券→选券→比价→积分评估"，长期降低单客成本 |
| 学生 / 预算敏感人群 | 结合团购券比价与积分兑换，用有限预算吃到更多 |
| 健身 / 控卡人群 | 结合营养数据做"热量预算内的省钱搭配" |
| 团购 App 用户 | 把手里囤的麦当劳团购券管起来，与官方券自动比较哪边更划算 |
| 企业行政 / 团餐组织者 | 团餐场景满减规则与助餐服务组合，降低团体订餐成本 |
| Agent / 效率工具玩家 | 将本仓库作为 Agent Skill（WorkBuddy / Claude Code 等）直接加载 |

## 📦 目录结构

```
maimai-saver/
├── SKILL.md                            # Agent Skill 入口：省钱方法论与调用规范
├── README.md                           # 本文件
├── LICENSE                             # MIT + 第三方条款声明
├── CONTEST_DECLARATION.md              # 参赛声明（麦当劳程序员创意开发大赛，官方原文）
├── MCP_INTEGRATION.md                  # MCP 集成说明：Server/Tool/调用流程/业务价值
├── mcp-config.example.json             # 脱敏 MCP 配置（仅环境变量占位符）
├── workbuddy.md                        # WorkBuddy 对话上下文（WorkBuddy 专项奖励核验）
├── config/
│   └── mcp.example.json                # MCP 客户端配置示例（占位符 Token）
├── scripts/
│   ├── mcd_client.py                   # MCP Streamable HTTP 客户端核心（纯标准库）
│   ├── mcd.py                          # CLI：check / tools / schema / call
│   └── deal_compare.py                 # 全渠道比价引擎（美团/抖音团购券手动录入）
├── references/
│   ├── tools.md                        # 35 个工具完整目录
│   ├── money-saving-strategies.md      # 十一大省钱策略详解（核心参考）
│   ├── group-buy-comparison.md         # 外部团购比价方法论
│   ├── workflows.md                    # 业务工作流详解（含省钱检查前置流程）
│   └── error-handling.md               # 错误处理与排查指南
├── examples/
│   └── order-flow-example.md           # 完整省钱点餐示例会话
└── .github/workflows/ci.yml            # 语法检查 CI
```

## 🚀 快速开始

### 第 1 步：申请 MCP Token

1. 打开 <https://open.mcd.cn/mcp>，右上角【登录】（手机号验证）
2. 【控制台】→【激活】→ 同意服务协议 → 复制 MCP Token

### 第 2 步（方式 A）：MCP 客户端直连

将 [`config/mcp.example.json`](config/mcp.example.json) 中的 `YOUR_MCP_TOKEN`
替换为实际 Token，写入你的 MCP 客户端配置：

| 客户端 | 配置位置 |
|---|---|
| WorkBuddy | `~/.workbuddy/mcp.json` |
| Cursor | 设置 → Tools & MCP → mcp.json |
| Cherry Studio / Trae / VSCode / Kiro | 各自 MCP 设置页（JSON 导入） |

### 第 2 步（方式 B）：独立 CLI

```bash
git clone https://github.com/<你的用户名>/maimai-saver.git
cd maimai-saver

# 提供 Token（三选一）
export MCD_MCP_TOKEN="你的Token"          # 环境变量（推荐）
echo "你的Token" > ~/.mcd_mcp_token        # 或 Token 文件
# 或每次调用时 --token "你的Token"

python scripts/mcd.py check                # 验证 Token 与连通性
python scripts/mcd.py tools                # 列出全部 35 个工具
python scripts/mcd.py schema query-meals   # 查看工具入参 Schema
python scripts/mcd.py call available-coupons   # 试试查可领的麦麦省券
```

**CLI 退出码**：`0` 成功 · `1` 工具错误 · `2` 鉴权失败 · `3` 限流 · `4` 网络错误

### 第 3 步（可选）：全渠道比价（美团/抖音团购券）

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
> [`references/group-buy-comparison.md`](references/group-buy-comparison.md)。

## 🧰 工具能力总览（35 个）

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

## 🤖 作为 Agent Skill 使用

将本仓库克隆到 Agent 的技能目录（如 WorkBuddy 的 `~/.workbuddy/skills/` 或
项目级 `.workbuddy/skills/`），Agent 即可依据 `SKILL.md` 中的触发词与工作流
自动调用：

```bash
git clone https://github.com/<你的用户名>/maimai-saver.git ~/.workbuddy/skills/maimai-saver
```

Skill 内置四条规范，确保 Agent 行为可控且省钱可验证：

1. **先查后改**：所有写操作前必须先完成查询，上下文齐备。
2. **下单必确认**：任何下单/取消/兑换/抽奖操作前，必须向用户展示关键信息并获得明确确认；支付链接仅原样转交，由用户自行支付。
3. **省钱必检查**：下单前执行"领券→选券→比价→积分抵扣评估"四步检查，报价附带省钱明细。
4. **不虚构优惠**：每一笔优惠金额必须来自 `calculate-price` 等工具的实际返回值。

## 🛡️ 错误处理

| 场景 | 行为 |
|---|---|
| HTTP 401 | 抛出 `AuthError`，提示重新申请 Token，不重试 |
| HTTP 429 | 指数退避 + 抖动自动重试（默认 3 次），尊重 `Retry-After` |
| HTTP 5xx / 网络错误 | 自动重试（默认 3 次） |
| 工具业务错误 | 抛出 `McpToolError`（含原始数据），建议用 `schema` 核对参数后修正 |

详见 [`references/error-handling.md`](references/error-handling.md)。

## 🧪 开发与测试

```bash
# 语法检查（与 CI 一致）
python -m py_compile scripts/mcd_client.py scripts/mcd.py

# CLI 冒烟
python scripts/mcd.py --help
python scripts/mcd.py call --help
```

CI（`.github/workflows/ci.yml`）在每次 push / PR 时自动执行上述检查。

## 🤝 贡献

欢迎通过 Issue / PR 参与：新增工作流文档、英文 README、工具目录更新
（麦当劳 MCP 版本迭代较快，以 `tools` 子命令的实时结果为准）。


## 📄 许可证

本项目代码以 [MIT](LICENSE) 许可证发布。

注意：本项目的运行依赖麦当劳中国 MCP 服务及其上游集成指南仓库
（[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server)），
相关服务的使用须另行遵守麦当劳中国的《使用条款》《麦当劳 MCP 服务规则》
及上游仓库的使用限制（个人非商业用途等）。
