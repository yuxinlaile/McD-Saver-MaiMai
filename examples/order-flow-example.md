# 示例：一次完整的省钱点餐会话

> 以下演示方式 B（CLI）的完整流程。方式 A（MCP 客户端直连）中的工具调用
> 逻辑完全一致。示例中的编码与金额均为示意，实际以服务器返回为准。
> Token 已通过环境变量 `MCD_MCP_TOKEN` 提供。

## 第 0 步：连通性检查

```bash
$ python scripts/mcd.py check
[OK] 连接成功
  服务器: mcd-mcp v1.0.0
  地址: https://mcp.mcd.cn
  可用工具数: 35
```

## 第 1 步：省钱检查 · 领券（策略 1）

```bash
$ python scripts/mcd.py call available-coupons
→ 返回可领的麦麦省券列表，向用户展示
$ python scripts/mcd.py call auto-bind-coupons        # 用户同意后执行（写操作）
```

## 第 2 步：查询配送地址

```bash
$ python scripts/mcd.py call delivery-query-addresses --raw
{
  "content": [{
    "type": "text",
    "text": "{\"addresses\":[{\"addressId\":\"A10086\",\"label\":\"家\",\"detail\":\"北京市朝阳区xx路xx号\"}]}"
  }]
}
```

→ 得到 `addressId: A10086`。

## 第 3 步：查询可配送门店

```bash
$ python scripts/mcd.py call delivery-query-stores --arg addressId=A10086
```

→ 返回附近可配送门店，选定 `storeCode: ST00123`（向用户确认）。

## 第 4 步：浏览菜单并查看套餐详情（策略 4：零成本替换）

```bash
$ python scripts/mcd.py call query-meals --arg storeCode=ST00123
$ python scripts/mcd.py call query-meal-detail --arg mealCode=MC0004567
```

→ 用户选择巨无霸套餐（`MC0004567`）。
→ 省钱动作：详情返回显示中可乐可零成本替换为零度可乐，主动推荐。

## 第 5 步：省钱检查 · 选券（策略 2）

```bash
$ python scripts/mcd.py call query-store-coupons --args '{"storeCode": "ST00123", "orderType": 2}'
```

→ 从返回的可用券中，筛选对当前购物车最优的 `couponId: CPN20261001`。

## 第 6 步：省钱检查 · 双价比价（策略 3）

```bash
$ python scripts/mcd.py call calculate-price --args '{ ...同下，但不带 couponId... }'
$ python scripts/mcd.py call calculate-price --args '{
  "storeCode": "ST00123",
  "products": [{"mealCode": "MC0004567", "quantity": 1, "options": [{"replace": "zero-cola"}]}],
  "couponId": "CPN20261001"
}'
```

→ 展示省钱明细：

```
商品原价：  ¥48.5（商品 ¥39.5 + 配送费 ¥9）
优惠券：    -¥10.0（麦乐送满39减10）
实付：      ¥38.5   （节省 ¥10.0 / 21%）
```

## 第 7 步：省钱检查 · 积分抵扣评估（策略 5）

```bash
$ python scripts/mcd.py call query-my-account
$ python scripts/mcd.py call mall-points-products
```

→ 积分 1200 分（无临期积分）；商城暂无低于当前方案折算价的同款券 →
   建议走"现金 + 券"方案，本次不消耗积分。

## 第 8 步：向用户确认（必须）

> 复述订单要点：门店、商品与替换项、优惠券、**省钱明细**、实付总价、配送地址。
> 仅当用户**明确确认**（如"确认下单"）后才执行下一步。

## 第 9 步：创建订单

```bash
$ python scripts/mcd.py call create-order --args '{ ...同上，含就餐方式 delivery... }'
```

→ 返回订单号 `OD20261010xxxx` 与支付链接。
→ **支付链接原样转交用户**，由用户自行在麦当劳渠道完成支付。

## 第 10 步：跟踪订单

```bash
$ python scripts/mcd.py call query-order --arg orderId=OD20261010xxxx
```

→ 状态：商家已接单 → 骑手已取餐 → 已送达。

## 异常分支示例

- 用户在支付前反悔：`query-order` 核对状态 → 用户确认 →
  `python scripts/mcd.py call cancel-order --arg orderId=OD20261010xxxx`
- 调用报 401：`exit code = 2`，按提示到 open.mcd.cn/mcp 换新 Token 后重试。
- 用户明确说"不用优惠直接下单"：跳过第 1/5/7 步，但仍展示无优惠价格。
