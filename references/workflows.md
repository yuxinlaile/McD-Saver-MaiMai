# 业务工作流详解

> 所有流程遵循三条铁律：
> 1. **先查后改** —— 写操作前必须完成全部查询，上下文齐备。
> 2. **下单必确认** —— `create-order` / `mall-create-order` / `party-order-create`
>    执行前，必须向用户展示关键信息并获得明确确认。
> 3. **省钱必检查** —— 下单前执行"省钱四步检查"（见下），并展示省钱明细。

## 工作流 0：下单前省钱检查（强制前置）

```
[1] available-coupons → 用户同意 → auto-bind-coupons   # 领券
    （CLI 用户：python scripts/mcd.py claim —— 展示清单 → y 确认 → 一键领取；
      无定时/无人值守模式，风控安全优先）
[2] query-store-coupons（门店 + orderType）             # 选券
[3] calculate-price（无券）vs calculate-price（带券）   # 比价，展示省钱明细
[4] query-my-account → mall-points-products            # 积分抵扣评估
[5]（可选）deal_compare.py compare                     # 结合用户录入的团购券做全渠道比价
```

十一大策略详解见 `money-saving-strategies.md`（含策略 11 全渠道比价）；
团购比价口径见 `group-buy-comparison.md`。以下各点餐工作流中的
"[省钱检查]"均指本流程。

## 工作流 1：麦乐送（外送）点餐

```
[1] delivery-query-addresses
     └─ 无地址 → 引导用户提供地址信息 → delivery-create-address → 回到 [1]
[2] delivery-query-stores        # 确定配送门店（多店时让用户选或选最近）
[3] query-meals                  # 拉取菜单（分类/编码/标签）
[4] query-meal-detail            # 套餐查看组成与可替换项（按需，逐个商品）
[5] query-store-coupons          # 门店可用券；可配合 available-coupons 先领券
[6] calculate-price              # 试算：商品金额 + 配送费 - 优惠 = 应付
[7] ★ 用户确认订单明细与总价
[8] create-order                 # 返回订单详情 + 支付链接
     └─ 支付链接原样转交用户，由用户自行支付
[9] query-order                  # 按需跟踪订单状态与配送进度
```

**分支处理**：
- 用户想换套餐内商品/特制 → 在 [4] 中确认可替换项后，替换信息进入 [6] 的商品参数。
- 用户要求预约时间下单 → `create-order` 支持预约功能（v1.0.4+），参数以 Schema 为准。
- 下单后要取消 → 先 `query-order` 核对状态，再 `cancel-order`（仅限可取消状态）。

## 工作流 2：到店取餐 / 堂食 / 得来速

```
[1] query-nearby-stores          # 用户提供地址 → 附近门店
[2] query-meals → query-meal-detail
[3] query-store-coupons → calculate-price
[4] ★ 用户确认
[5] create-order                 # 就餐方式：堂食/外带/得来速
     └─ 堂食/外带场景可返回取餐柜二维码（v1.0.9）
[6] query-order
```

## 工作流 3：优惠券场景

```
领券：available-coupons → ★确认 → auto-bind-coupons（一键领取全部可领券）
查券：query-my-coupons / query-store-coupons
用券：calculate-price（无券）vs calculate-price（带券）双价对比，
      展示省钱明细后，确认优惠生效再进入下单确认
```

## 工作流 4：积分与麦麦商城

```
查积分：query-my-account          # 关注"即将过期积分"，主动提醒用户
兑换：  query-my-account → mall-points-products → mall-product-detail
        → ★确认（商品、积分消耗、兑换后余额）→ mall-create-order
查单：  mall-order-list → mall-order-detail
```

## 工作流 5：积分抽奖

```
query-lottery-info               # 活动状态、消耗规则、可用次数/积分
 → 告知用户消耗规则 → ★确认 → draw-lottery
 → query-my-prizes（查历史奖品）
```

## 工作流 6：主题活动预约（派对/品鉴会）

严格级联，不可跳步：

```
query-party-city
 → query-party-store（城市）
 → query-partystore-date（门店）
 → query-partystore-session（门店+日期）
 → ★用户确认：城市/门店/日期/场次
 → party-order-create
```

## 工作流 7：营养咨询

```
list-nutrition-foods
 → 按用户目标（减脂/控钠/指定热量）筛选与组合
 → 如需下单，转入工作流 1/2
```

## 工作流 8：企业团餐

```
query-nearby-stores / delivery-query-stores
 → query-meal-assistance         # 查询该门店支持的助餐服务（仅团餐场景）
 → query-meals → calculate-price
 → ★确认 → create-order（团餐就餐方式）
```

## 辅助判断

- 涉及"现在""今天""活动什么时候开始"等时间判断 → 先 `now-time-info`。
- 用户问"最近有什么活动" → `campaign-calendar`。
