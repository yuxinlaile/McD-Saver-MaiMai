# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循语义化版本（SemVer）。

## [1.2.1] - 2026-10-10

### Added
- `requirements-dev.txt`：声明开发与测试依赖（pytest）；CI 改为安装该文件
- 单元测试新增：SSE 流 CRLF 换行兼容用例、重试退避计算边界用例

### Changed
- `mcd_client.py` 内部重构（公开接口与行为完全兼容）：提取 `_jsonrpc()` 消除
  initialize/tools/list/tools/call 三处的重复消息构造；提取 `_compute_backoff()`
  与 `_parse_retry_after()` 统一 429/5xx/网络错误的退避计算；`import sys` 归位模块顶部
- `_parse_sse()` 增加 CRLF/CR 换行归一化，兼容不同服务器的 SSE 帧分隔风格
- `deal_compare.py`：券有效期徽标逻辑收敛为 `_validity_badge()`，消除两处重复

### Fixed
- 修正 `McdMcpClient` docstring 中默认地址的笔误（mcd.mcd.cn -> mcp.mcd.cn）
- 清理 `mcd_client.py` 未使用的 `Union` 类型导入

## [1.2.0] - 2026-10-10

### Added
- 单元测试套件 `tests/`（43 个用例）：SSE 解析、Token 三通道解析、客户端
  请求头与响应解码、比价折算/排序/有效期判定、provider 数据源接口、
  CLI 退出码与全流程冒烟；CI 增加 pytest 步骤
- `deal_compare.py` 数据源 provider 接口：通过环境变量
  `MAIMAI_DEALS_PROVIDER` 指定外部数据源模块（需实现 `load_deals()`），
  为团购平台未来开放官方 API 预留自动化接入点，失败自动回退本地券库
- 英文说明文档 `README_EN.md`、版本变更记录 `CHANGELOG.md`
- 各主流 Agent 安装指南 `references/agent-skill-installation.md`
  （WorkBuddy / Claude Code / Cursor / OpenAI Codex，基于开放 Agent Skills 标准）
- README 效果预览：横幅与比价报告图（`docs/assets/*.svg`）
- GitHub Issue 模板（Bug 报告 / 功能建议）与 PR 模板（含自检清单）

### Changed
- 仓库内容清理：`workbuddy.md` 由占位模板改为真实开发对话上下文记录
  （敏感凭证脱敏）；README 移除悬空链接；MCP 配置示例的 Token 占位符
  统一为 `${MCD_MCP_TOKEN}` 环境变量形式；CI 语法检查纳入 `deal_compare.py`

## [1.1.0] - 2026-10-10

### Added
- 技能定位重构为"麦麦省钱助手"（maimai-saver）：省钱顾问方法论——
  下单前省钱四步检查（领券→选券→双价比价→积分抵扣评估），
  "先查后改 / 下单必确认 / 不虚构优惠"调用规范
- 全渠道比价引擎 `scripts/deal_compare.py`：美团/抖音等团购券手动录入
  本地券库，与官方渠道（MCP calculate-price）同口径估算比价并输出推荐
- 参考文档：`references/money-saving-strategies.md`（十一大策略）、
  `references/group-buy-comparison.md`（比价方法论）
- 大赛参赛文件：`CONTEST_DECLARATION.md`、`MCP_INTEGRATION.md`、
  `mcp-config.example.json`、`workbuddy.md`

### Changed
- 工具目录按实测校准为 35 个（新增 `query-survey-coupon`、`query-promotions`）

## [1.0.0] - 2026-10-10

### Added
- 首个版本：基于麦当劳中国官方 MCP Server（https://mcp.mcd.cn，
  Streamable HTTP）的技能包
- 纯标准库 MCP 客户端：完整 JSON-RPC 生命周期、Mcp-Session-Id 会话保持、
  JSON/SSE 双格式响应解析；401 快速失败、429 指数退避 + 抖动重试
  （尊重 Retry-After）、5xx/网络错误自动重试
- CLI（check / tools / schema / call），结构化退出码 0/1/2/3/4
- Agent Skill 入口 `SKILL.md` 与 references 参考文档（工具目录、工作流、
  错误排查）、GitHub Actions CI、MIT LICENSE（含第三方条款声明）
