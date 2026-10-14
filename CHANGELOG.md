# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循语义化版本（SemVer）。

## [1.6.0] - 2026-10-14

### Added
- **用券排程**（silent_cost）：临期券过期窗口 × 历史点单频率 →
  把券按面值降序排入窗口内预期点单次数，一次算清
  「名义面值 → 可实现 → 注定过期」——券不是越多越好，用得上才算数
- **券面值实测**（silent_cost `--probe`）：无面值字段/标题无金额的券，
  券商品码 + couponId 传官方 calculate-price 实测精确价值——
  实测优先、估算兜底、失败如实标注（与社区同类工具的实测口径对齐）
- **单文件 HTML 报告**（silent_cost `--html`）：零 CDN、零脚本、
  双击打开即可截图分享的「体检长图」，卡号类敏感字段不输出
- **30 秒离线全链路演示**（根目录 `demo.py` + `fixtures/`）：
  与真实 MCP 响应同格式的数据快照，原样跑通四步检查全链路——
  **demo 即回归测试**（tests/test_demo_pipeline.py 断言其输出）
- **真实性资产**：真实运行输出渲染的终端截图入 README（标注日期与「未美化」）、
  「还可以这样问」指令映射表、mermaid 全渠道架构图、README 差异化对比表
- **examples/verified-run.md**：真实 Token 运行验证记录的留档模板与流程
- pyproject.toml：包元数据与 pytest 配置（`pip install .` 可用，运行时仍零依赖）

### Testing
- 单元测试 98 → 113（用券排程 / 券面值实测 / HTML 报告 / demo 全链路回归）

## [1.5.0] - 2026-10-13

### Added
- optimizer.py：**营养约束**——`--min-protein`（蛋白质下限，g）与
  `--max-sodium`（钠上限，mg），配合菜单条目的 `protein`/`sodium` 字段
  （来自 list-nutrition-foods）生效；违规方案排后并如实标注
  「蛋白质不足 xx g / 超钠 xx mg」；**营养数据缺失的方案按不满足处理**
  并标注「蛋白质未知」——延续"算不出如实披露"原则，绝不虚构达标。
  健身增肌与控盐人群场景
- demo.html 页脚增加 GitHub Star 引导链接
- 单元测试 89 → 98（新增营养约束用例：达标不打标 / 不足排后 /
  数据缺失保守处理 / 组合约束排序 / 报告文案）

## [1.4.2] - 2026-10-12

### Added
- demo.html 试算页大幅扩充：31 项菜单（7 大类，含早餐段）、9 张券、
  6 单美团/抖音团购示例（费率计价）、跨渠道终局建议区块、分享按钮
- demo.html 新增**导入真实菜单**：粘贴 MCP `query-meals` 原始输出即可全量
  替换示例数据（宽容字段解析 + 逐条校验），作为官方菜单全量同步的合规路径
- 新增 GitHub Issue 模板（bug 反馈 / 功能建议 / 引导讨论区）

## [1.4.1] - 2026-10-12

### Added
- `mcd.py` 新增 `claim` 子命令：列出麦麦省可领券（available-coupons）→
  展示清单 → 交互确认（y/N，`--yes` 供脚本场景）→ auto-bind-coupons 一键领取。
  安全边界：用户主动触发、单次执行；**明确不提供定时轮询与无人值守后台**
  （此类自动化有 Token 风控封禁风险，与 SKILL.md「下单必确认」规范一致）
- 单元测试 84 → 89（claim 流程用例：直接领取/确认领取/取消/空清单/大小写）

## [1.4.0] - 2026-10-12

### Added
- optimizer.py：**多约束支持**——`--budget` 实付预算上限与 `--max-kcal` 热量上限
  （菜单含 kcal 字段时生效），违反约束的方案排后并标注"超预算/超热量 xx"，
  不静默删除；**套餐替换枚举**——套餐含 `contains` 字段覆盖全部想吃单品时
  自动生成"改点套餐"候选，是否更省交给计价排名判断
- silent_cost.py：**积分影子价格**——`--mall` 传入积分商城商品列表后，
  按 max(面值÷积分) 估算最优兑换效率并给出可用积分折现值
  （统一成本口径）
- 单元测试 75 → 89（新增约束/套餐替换/影子价格用例）

### Changed
- SKILL.md 工作流 5 补充约束参数说明；README 中英运行与命令同步

### 致谢
- 本版吸收了大赛社区项目的公开思路：YOMXXX/McOptima 的多约束求解、
  akexin/mcd-points-actuary 的积分影子价格、BreadKid/mcd-order-calories 的
  "算不出如实披露"原则

## [1.3.0] - 2026-10-12

### Added
- 券组合优化器 `scripts/optimizer.py`：确定性枚举「无券直点 / 单券 /
  凑单达标」候选方案，输出最优组合与 Top-N 备选；计价可插拔——估算模式
  （本地价格表）或 `--mcp` 真实计价模式（官方 calculate-price 逐方案核价）；
  凑单方案强制标注"仅当你本来就需要该商品才划算"，并以"不凑单"为基准排序
- 沉默成本体检 `scripts/silent_cost.py`：临期券扫描（7 天内到期按面值合计）+
  消费画像（订单数/总支出/客单价/高频复购单品）+ 积分体检（可用与即将过期），
  字段宽容匹配、识别不到明确标注"未识别"
- GitHub Pages 在线试算器 `docs/demo.html`：optimizer 算法前端复刻 + 内嵌示例
  数据，免登录免 Token 开箱即验；界面采用双栏卡片式布局（桌面端左选右算、
  移动端自适应），整卡点选 + 数量步进器，凑单陷阱独立警示样式，支持一键重置
- `install.ps1`：Windows 一键安装脚本（备份旧版本，不触碰 Token 与连接器）
- 预览图 `docs/assets/optimizer-report.svg`；单元测试 49 → 84（新增优化器与
  体检模块用例）
- README（中英）头部新增在线试算与 Release 徽章

### Changed
- SKILL.md：工具地图与标准工作流新增"最优组合点单"与"沉默成本体检"两条
  工作流；版本号升至 1.3.0
- README（中英）：核心功能、运行与命令、目录结构、效果预览同步更新

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
