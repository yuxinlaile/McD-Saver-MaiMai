#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦麦省钱助手 —— 沉默成本体检。

回答一个省钱工具很少回答的问题：「你正在白扔多少钱？」

四部分（全部来自官方 MCP 只读工具，零风险）：

- 临期券扫描：7 天内到期的券按面值合计，列出优先处理清单；
- 用券排程（v1.6）：过期窗口 × 历史点单频率 → 推算窗口内实际能消耗的
  点单次数，把券按净价值排序排入点单——「可实现金额」与「注定过期金额」
  一次算清。券不是越多越好，用得上才算数；
- 消费画像：近 N 单的订单数 / 总支出 / 客单价 / 高频复购单品
  （复购 ≥2 次的单品提示改套餐的省钱方向）；
- 积分体检：可用积分与本月/下月即将过期积分。

券面值实测（--probe，v1.6）：无面值字段/标题无金额的券，把券自带的商品码
与 couponId 传给官方 calculate-price，返回的 discount 即该券精确价值——
实测优先、估算兜底，绝不虚构。

数据获取（Agent 按 SKILL.md 工作流执行，JSON 原样保存即可）：

    python scripts/mcd.py call query-my-coupons --raw > coupons.json
    python scripts/mcd.py call order-list --raw > orders.json
    python scripts/mcd.py call query-my-account --raw > points.json
    python scripts/silent_cost.py report --coupons coupons.json --orders orders.json \
        --points points.json

解析策略：对每个字段做宽容匹配（常见命名变体 + 标题正则兜底），
识别不到的字段明确标注"未识别"，绝不猜测编造。

示例::

    python scripts/silent_cost.py demo                          # 离线演示
    python scripts/silent_cost.py demo --html report.html       # 生成可分享单文件 HTML
    python scripts/silent_cost.py report --coupons c.json --probe --store-code ST001
退出码：0 成功 · 1 用法/数据错误
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

EXIT_OK = 0
EXIT_USAGE = 1

EXPIRING_DAYS = 7

# 常见字段命名变体（按优先级）
FACE_KEYS = ["parValue", "faceValue", "worth", "face", "discountValue"]
EXPIRE_KEYS = ["validityEndTime", "validUntil", "endTime", "expireTime", "expireDate"]
AMOUNT_KEYS = ["totalAmount", "payable", "payAmount", "amount", "totalPrice", "total"]
TIME_KEYS = ["createTime", "orderTime", "ctime", "time", "orderDate"]
NAME_KEYS = ["name", "title", "dishName", "productName"]
POINTS_AVAILABLE_KEYS = ["availablePoint", "availablePoints", "points", "balance"]
POINTS_EXPIRE_KEYS = ["currentMouthExpirePoint", "nextMouthExpirePoint",
                      "expirePoint", "expiringPoints"]


# ---------------------------------------------------------------------------
# 宽容字段提取
# ---------------------------------------------------------------------------
def _first_key(obj: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return None


def _unwrap(raw: Any) -> List[Dict[str, Any]]:
    """从工具原始响应中提取记录数组：兼容 {"data": [...]} / {"data": {"list": [...]}} / [...]。"""
    data = raw
    if isinstance(raw, dict) and "content" in raw:  # tools/call 标准响应壳
        texts = [c.get("text", "") for c in raw["content"] if isinstance(c, dict) and c.get("type") == "text"]
        for text in texts:
            try:
                data = json.loads(text)
                break
            except (ValueError, TypeError):
                continue
    if isinstance(data, dict):
        for key in ("data", "coupons", "orders", "list", "records", "items"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
        return []
    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


def _parse_amount(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"(\d+(?:\.\d+)?)", value.replace(",", ""))
        if match:
            return float(match.group(1))
    return None


def _parse_expire_days(value: Any, today: datetime) -> Optional[int]:
    """解析有效期并返回距今天数；支持日期字符串与毫秒时间戳。"""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        # 毫秒时间戳（13 位）或秒时间戳（10 位）
        seconds = float(value) / 1000.0 if float(value) > 1e12 else float(value)
        try:
            end = datetime.fromtimestamp(seconds)
            return (end.date() - today.date()).days
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            end = datetime.strptime(text[: len(fmt) + 2].strip(), fmt)
            return (end.date() - today.date()).days
        except ValueError:
            continue
    match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if match:
        try:
            end = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return (end.date() - today.date()).days
        except ValueError:
            return None
    return None


def _coupon_face(coupon: Dict[str, Any]) -> Optional[float]:
    face = _parse_amount(_first_key(coupon, FACE_KEYS))
    if face is not None:
        return face
    title = str(coupon.get("title") or coupon.get("couponName") or "")
    match = re.search(r"(?:减|抵)(\d+(?:\.\d+)?)", title)
    if match:
        return float(match.group(1))
    match = re.search(r"(\d+(?:\.\d+)?)\s*元", title)
    if match:
        return float(match.group(1))
    return None


# ---------------------------------------------------------------------------
# 分析逻辑
# ---------------------------------------------------------------------------
def analyze_coupons(coupons_raw: Any, today: Optional[datetime] = None) -> Dict[str, Any]:
    today = today or datetime.now()
    records = _unwrap(coupons_raw)
    expiring: List[Dict[str, Any]] = []
    unrecognized = 0
    for coupon in records:
        days = _parse_expire_days(_first_key(coupon, EXPIRE_KEYS), today)
        face = _coupon_face(coupon)
        if days is None:
            unrecognized += 1
            continue
        if 0 <= days <= EXPIRING_DAYS:
            title = str(coupon.get("title") or coupon.get("couponName") or coupon.get("couponId") or "未命名券")
            expiring.append({"title": title, "face": face, "days": days,
                             "couponId": coupon.get("couponId"),
                             "productCode": _first_key(coupon, ["productCode", "itemCode", "goodsCode", "mealCode"])})
    expiring.sort(key=lambda c: c["days"])
    return {
        "total": len(records),
        "expiring": expiring,
        "expiring_face_total": sum(c["face"] or 0.0 for c in expiring),
        "unrecognized": unrecognized,
    }


def analyze_orders(orders_raw: Any, today: Optional[datetime] = None) -> Dict[str, Any]:
    today = today or datetime.now()
    records = _unwrap(orders_raw)
    amounts: List[float] = []
    order_days: List[datetime] = []
    item_counter: Dict[str, int] = {}
    unrecognized = 0
    for order in records:
        amount = _parse_amount(_first_key(order, AMOUNT_KEYS))
        if amount is None:
            unrecognized += 1
        else:
            amounts.append(amount)
        when = _first_key(order, TIME_KEYS)
        if when is not None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
                try:
                    order_days.append(datetime.strptime(str(when)[:len(fmt) + 2].strip(), fmt))
                    break
                except ValueError:
                    continue
        items = order.get("items") or order.get("orderItems") or order.get("products") or []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    name = _first_key(item, NAME_KEYS)
                    qty = item.get("quantity") or item.get("count") or 1
                else:
                    name, qty = item, 1
                if name:
                    item_counter[str(name)] = item_counter.get(str(name), 0) + max(1, int(qty or 1))
    top_items = sorted(item_counter.items(), key=lambda kv: kv[1], reverse=True)[:3]
    total = sum(amounts)
    # 点单频率：以最早订单日为观测起点（含当天），单位：单/天
    frequency = None
    if order_days:
        span = max((today - min(order_days)).days, 1)
        frequency = len(order_days) / span
    return {
        "order_count": len(records),
        "amount_count": len(amounts),
        "total_spend": total if amounts else None,
        "avg_ticket": (total / len(amounts)) if amounts else None,
        "order_frequency": frequency,
        "top_items": [{"name": n, "count": c} for n, c in top_items if c >= 2],
        "unrecognized": unrecognized,
    }


# ---------------------------------------------------------------------------
# 用券排程（v1.6）：过期窗口 × 点单频率 → 可实现 vs 注定过期
# ---------------------------------------------------------------------------
def schedule_coupons(coupons: Dict[str, Any], orders: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """把临期券按面值降序排入「过期窗口内的预期点单次数」。

    窗口 = 临期券中最早到期的天数（全部可用的期限内）；预期点单次数 =
    点单频率 × 窗口（向下取整，至少 1）。排不进点单的券标记为注定过期——
    名义面值再高，用不上就不算钱。数据不足（无频率或无临期券）返回 None。
    """
    expiring = [c for c in coupons.get("expiring", []) if c.get("face") is not None]
    frequency = orders.get("order_frequency")
    if not expiring or frequency is None:
        return None
    window = max(min(c["days"] for c in expiring), 1)
    expected_orders = max(1, int(frequency * window))
    ranked = sorted(expiring, key=lambda c: (c["face"] or 0.0), reverse=True)
    scheduled, missed = [], []
    for idx, coupon in enumerate(ranked):
        entry = dict(coupon)
        if idx < expected_orders:
            entry["slot"] = "第 {0} 单".format(idx + 1)
            scheduled.append(entry)
        else:
            entry["slot"] = "排不上"
            missed.append(entry)
    realizable = sum(c["face"] for c in scheduled)
    doomed = sum(c["face"] for c in missed)
    return {
        "window_days": window,
        "expected_orders": expected_orders,
        "frequency": frequency,
        "scheduled": scheduled,
        "missed": missed,
        "realizable": realizable,
        "doomed": doomed,
        "face_total": realizable + doomed,
    }


# ---------------------------------------------------------------------------
# 券面值实测（v1.6）：calculate-price 带 couponId 实测，估算兜底
# ---------------------------------------------------------------------------
def probe_coupon_value(client: Any, coupon: Dict[str, Any]) -> Optional[float]:
    """把券商品码（若有）与 couponId 传给官方 calculate-price，实测券精确价值。

    返回值口径：响应中的 discount 字段（券抵扣金额）。任何一步解析失败
    返回 None——调用方应保留估算值并标注「估算」，绝不虚构实测结果。
    """
    product_code = coupon.get("productCode")
    coupon_id = coupon.get("couponId")
    if not coupon_id:
        return None
    products = [{"mealCode": product_code, "quantity": 1}] if product_code else []
    args: Dict[str, Any] = {
        "storeCode": getattr(client, "_store_code", ""),
        "orderType": getattr(client, "_order_type", 1),
    }
    if products:
        args["products"] = products
    args["couponId"] = coupon_id
    try:
        result = client.call_tool("calculate-price", args)
    except Exception:  # noqa: BLE001 - 工具层任何失败都不应中断体检
        return None
    data = result.get("data", result) if isinstance(result, dict) else {}
    discount = None
    for key in ("discount", "couponDiscount", "discountAmount", "couponAmount"):
        value = _first_key(data, [key]) if isinstance(data, dict) else None
        parsed = _parse_amount(value)
        if parsed is not None:
            discount = parsed
            break
    return discount


def analyze_points(points_raw: Any) -> Dict[str, Any]:
    if not isinstance(points_raw, dict) and not isinstance(points_raw, list):
        return {"available": None, "unrecognized": 1}
    data: Any = points_raw
    if isinstance(points_raw, dict) and "content" in points_raw:
        data = _unwrap({"content": points_raw["content"], "keep": 1})  # 复用文本壳解包
        data = data[0] if data else points_raw
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        return {"available": None, "unrecognized": 1}
    inner = data.get("data") if isinstance(data.get("data"), dict) else data
    available = _parse_amount(_first_key(inner, POINTS_AVAILABLE_KEYS))
    expiring_now = _parse_amount(_first_key(inner, ["currentMouthExpirePoint"]))
    expiring_next = _parse_amount(_first_key(inner, ["nextMouthExpirePoint"]))
    return {"available": available, "expiring_now": expiring_now,
            "expiring_next": expiring_next,
            "unrecognized": 0 if available is not None else 1}


def analyze_mall(mall_raw: Any) -> Dict[str, Any]:
    """积分商城影子价格：max(面值 ÷ 积分) = 这些积分最优兑换能换回的现金效率。

    mall_raw 兼容 {"data": [...]} 与 [...]，商品需含积分与面值字段
    （常见命名：points/needPoint 与 worth/price/faceValue）。
    """
    products = _unwrap(mall_raw) if mall_raw else []
    best: Optional[Dict[str, Any]] = None
    for p in products:
        pts = _parse_amount(_first_key(p, ["points", "needPoint", "point", "price2"]))
        worth = _parse_amount(_first_key(p, ["worth", "price", "faceValue", "value"]))
        name = _first_key(p, NAME_KEYS) or "未命名商品"
        if pts and pts > 0 and worth is not None:
            efficiency = worth / pts
            if best is None or efficiency > best["efficiency"]:
                best = {"name": str(name), "points": pts, "worth": worth, "efficiency": efficiency}
    return {"shadow_price": best["efficiency"] if best else None,
            "best_product": best, "products": len(products)}


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------
def _fmt(value: Optional[float]) -> str:
    return "¥{0:.2f}".format(value) if value is not None else "未识别"


def render_report(coupons: Dict[str, Any], orders: Dict[str, Any],
                  points: Dict[str, Any], mall: Optional[Dict[str, Any]] = None,
                  schedule: Optional[Dict[str, Any]] = None) -> str:
    lines: List[str] = []
    lines.append("=" * 68)
    lines.append("麦麦省钱助手 · 沉默成本体检报告")
    lines.append("=" * 68)

    lines.append("")
    lines.append("【一】临期券（{0} 天内到期）".format(EXPIRING_DAYS))
    if coupons["expiring"]:
        for c in coupons["expiring"]:
            if c.get("face_source") == "measured":
                face = "¥{0:.2f}（实测）".format(c["face"])
            else:
                face = "¥{0:.2f}".format(c["face"]) if c["face"] is not None else "面值未识别（可用 --probe 实测）"
            lines.append("  · {0} ｜ {1} ｜ 还剩 {2} 天".format(c["title"], face, c["days"]))
        lines.append("  合计面值：{0}".format(_fmt(coupons["expiring_face_total"])))
        lines.append("  建议：优先用掉临期券——过期即沉没，凑单达标也比浪费划算。")
    else:
        lines.append("  近 {0} 天内没有临期券。".format(EXPIRING_DAYS))
    if coupons["unrecognized"]:
        lines.append("  （{0} 张券的有效期字段未识别，已跳过）".format(coupons["unrecognized"]))

    if schedule:
        lines.append("")
        lines.append("【一·B】用券排程（窗口 {0} 天 × 频率 {1:.3f} 单/天 ≈ {2} 单）".format(
            schedule["window_days"], schedule["frequency"], schedule["expected_orders"]))
        lines.append("  券不是越多越好，用得上才算数：")
        for c in schedule["scheduled"]:
            lines.append("    {0} → {1} ｜ {2} ｜ 净用掉 ¥{3:.2f}".format(
                c["slot"], c["title"], "还剩 {0} 天".format(c["days"]), c["face"]))
        if schedule["missed"]:
            lines.append("  排不上（注定随券过期浪费 ¥{0:.2f}）：".format(schedule["doomed"]))
            for c in schedule["missed"]:
                lines.append("    · {0} ｜ ¥{1:.2f} ｜ 还剩 {2} 天".format(c["title"], c["face"], c["days"]))
        lines.append("  名义 ¥{0:.2f} → 可实现 ¥{1:.2f}，注定过期 ¥{2:.2f}。".format(
            schedule["face_total"], schedule["realizable"], schedule["doomed"]))
        lines.append("  本月最该做的事：把排得上的券优先用掉——这笔钱不用就是纯损失。")

    lines.append("")
    lines.append("【二】消费画像（近 {0} 单）".format(orders["order_count"]))
    if orders["amount_count"]:
        lines.append("  订单数：{0} 单 ｜ 总支出：{1} ｜ 客单价：{2}".format(
            orders["order_count"], _fmt(orders["total_spend"]), _fmt(orders["avg_ticket"])))
        if orders["top_items"]:
            lines.append("  高频单品：")
            for item in orders["top_items"]:
                lines.append("    · {0} × {1} 次——若改点对应套餐，通常每单还能再省一些。".format(
                    item["name"], item["count"]))
    else:
        lines.append("  暂无可识别的历史订单金额。")
    if orders["unrecognized"]:
        lines.append("  （{0} 单金额字段未识别，已跳过）".format(orders["unrecognized"]))

    lines.append("")
    lines.append("【三】积分体检")
    if points["available"] is not None:
        lines.append("  可用积分：{0:.0f}".format(points["available"]))
        if points.get("expiring_now"):
            lines.append("  本月将过期：{0:.0f}（优先级最高，过期即清零）".format(points["expiring_now"]))
        if points.get("expiring_next"):
            lines.append("  下月将过期：{0:.0f}".format(points["expiring_next"]))
        lines.append("  建议：优先用积分兑换临期前会用到的餐品券。")
        if mall and mall.get("shadow_price"):
            shadow = mall["shadow_price"]
            lines.append("  积分价值参考：最优兑换「{0}」= {1:.4f} 元/积分"
                         "（口径：积分商城最优标的效率）".format(
                             mall["best_product"]["name"], shadow))
            lines.append("  可用积分折现 ≈ ¥{0:.2f}——用它判断「这单要不要动积分」的机会成本。".format(
                points["available"] * shadow))
    else:
        lines.append("  积分账户字段未识别（可先用 query-my-account 核对数据）。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 单文件 HTML 报告（v1.6）：零 CDN、双击打开即可截图分享
# ---------------------------------------------------------------------------
_HTML_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>麦麦省钱助手 · 沉默成本体检报告</title>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif;
         background: #FFF8EE; color: #292321; margin: 0; padding: 32px 16px; }}
  .card {{ max-width: 720px; margin: 0 auto 16px; background: #fff; border-radius: 14px;
          padding: 22px 26px; box-shadow: 0 2px 10px rgba(191,124,26,.12); }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 0 0 10px; color: #B0720F; letter-spacing: .5px; }}
  .sub {{ color: #8a7a66; font-size: 12px; margin-bottom: 14px; }}
  .row {{ display: flex; justify-content: space-between; padding: 7px 0;
          border-bottom: 1px dashed #f0e4d0; font-size: 14px; gap: 12px; }}
  .row:last-child {{ border-bottom: none; }}
  .money {{ font-variant-numeric: tabular-nums; font-weight: 600; white-space: nowrap; }}
  .good {{ color: #1a7f37; }} .bad {{ color: #c62828; }} .muted {{ color: #9a8b77; }}
  .stat {{ display: flex; gap: 10px; margin: 10px 0 2px; flex-wrap: wrap; }}
  .stat div {{ flex: 1; min-width: 130px; background: #FFF3DC; border-radius: 10px;
               padding: 10px 12px; text-align: center; }}
  .stat b {{ display: block; font-size: 20px; margin-top: 2px; }}
  footer {{ max-width: 720px; margin: 0 auto; text-align: center; color: #9a8b77;
            font-size: 11px; line-height: 1.8; }}
  footer a {{ color: #B0720F; }}
</style>
</head>
<body>
<div class="card">
  <h1>🍟 沉默成本体检报告</h1>
  <div class="sub">生成于 {generated} · 数据来自麦当劳官方 MCP 只读工具 · 金额为估算口径</div>
  {coupons_block}
</div>
<div class="card">
  <h2>【二】消费画像</h2>
  {orders_block}
</div>
<div class="card">
  <h2>【三】积分体检</h2>
  {points_block}
</div>
<footer>maimai-saver · 社区开源项目，与麦当劳公司无关联<br>
<a href="https://github.com/yuxinlaile/maimai-saver">GitHub 仓库</a> ·
<a href="https://yuxinlaile.github.io/maimai-saver/demo.html">在线试算</a> · 卡号/Token 已脱敏，可安全截图</footer>
</body>
</html>
"""


def render_html(coupons: Dict[str, Any], orders: Dict[str, Any],
                points: Dict[str, Any], mall: Optional[Dict[str, Any]] = None,
                schedule: Optional[Dict[str, Any]] = None,
                generated: Optional[str] = None) -> str:
    """生成零依赖单文件 HTML 报告——可直接截图分享的「体检长图」。"""
    now = generated or datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    if coupons["expiring"]:
        for c in coupons["expiring"]:
            face = "¥{0:.2f}".format(c["face"]) if c["face"] is not None else "未识别"
            src = ' <span class="good">实测</span>' if c.get("face_source") == "measured" else ""
            rows.append('<div class="row"><span>{0}</span><span class="money">{1}{2} · 还剩 {3} 天</span></div>'.format(
                _esc(c["title"]), face, src, c["days"]))

        stat = '<div class="stat"><div>临期面值合计<b class="money">{0}</b></div>'.format(_fmt_html(coupons["expiring_face_total"]))
        if schedule:
            stat += ('<div>窗口内可实现<b class="money good">{0}</b></div>'
                     '<div>注定过期<b class="money bad">{1}</b></div>').format(
                _fmt_html(schedule["realizable"]), _fmt_html(schedule["doomed"]))
        stat += "</div>"
        rows.append(stat)
        if schedule:
            for c in schedule["scheduled"]:
                rows.append('<div class="row"><span>🥇 {0} → {1}</span><span class="money good">{2}</span></div>'.format(
                    _esc(c["title"]), c["slot"], _fmt_html(c["face"])))
            for c in schedule["missed"]:
                rows.append('<div class="row"><span>⌛ {0}（排不上）</span><span class="money bad">{1}</span></div>'.format(
                    _esc(c["title"]), _fmt_html(c["face"])))
    else:
        rows.append('<div class="row"><span class="muted">近 {0} 天内没有临期券。</span></div>'.format(EXPIRING_DAYS))
    coupons_block = "<h2>【一】临期券（{0} 天内到期）</h2>".format(EXPIRING_DAYS) + "".join(rows)

    orows = []
    if orders["amount_count"]:
        orows.append('<div class="stat"><div>订单数<b>{0}</b></div><div>总支出<b class="money">{1}</b></div>'
                     '<div>客单价<b class="money">{2}</b></div></div>'.format(
            orders["order_count"], _fmt_html(orders["total_spend"]), _fmt_html(orders["avg_ticket"])))
        for item in orders["top_items"]:
            orows.append('<div class="row"><span>🔁 {0}</span><span>× {1} 次——改点对应套餐通常更省</span></div>'.format(
                _esc(item["name"]), item["count"]))
    else:
        orows.append('<div class="row"><span class="muted">暂无可识别的历史订单金额。</span></div>')
    orders_block = "".join(orows)

    prows = []
    if points["available"] is not None:
        prows.append('<div class="row"><span>可用积分</span><span class="money">{0:.0f}</span></div>'.format(points["available"]))
        if points.get("expiring_now"):
            prows.append('<div class="row"><span>本月将过期（优先级最高）</span><span class="money bad">{0:.0f}</span></div>'.format(points["expiring_now"]))
        if points.get("expiring_next"):
            prows.append('<div class="row"><span>下月将过期</span><span class="money">{0:.0f}</span></div>'.format(points["expiring_next"]))
        if mall and mall.get("shadow_price"):
            prows.append('<div class="row"><span>积分影子价格（最优兑换「{0}」）</span><span class="money">{1:.4f} 元/积分</span></div>'.format(
                _esc(mall["best_product"]["name"]), mall["shadow_price"]))
            prows.append('<div class="row"><span>可用积分折现</span><span class="money">≈ ¥{0:.2f}</span></div>'.format(
                points["available"] * mall["shadow_price"]))
    else:
        prows.append('<div class="row"><span class="muted">积分账户字段未识别。</span></div>')
    points_block = "".join(prows)

    return _HTML_TMPL.format(generated=_esc(now), coupons_block=coupons_block,
                             orders_block=orders_block, points_block=points_block)


def _esc(text: Any) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _fmt_html(value: Optional[float]) -> str:
    return "¥{0:.2f}".format(value) if value is not None else "—"


# ---------------------------------------------------------------------------
# 演示数据
# ---------------------------------------------------------------------------
DEMO_COUPONS = {"data": [
    {"title": "满50减12", "parValue": 12.0, "validityEndTime": "2026-10-13 23:59:59"},
    {"title": "免费脆薯饼", "parValue": 8.0, "validityEndTime": "2026-10-14 23:59:59"},
    {"title": "9.9元中杯冰美式", "parValue": 13.1, "validityEndTime": "2026-10-17 23:59:59"},
    {"title": "满30减5", "parValue": 5.0, "validityEndTime": "2026-12-31 23:59:59"},
]}
DEMO_ORDERS = {"data": [
    {"createTime": "2026-09-02", "totalAmount": 33.5,
     "items": [{"name": "麦辣鸡腿堡", "quantity": 1}]},
    {"createTime": "2026-09-11", "totalAmount": 36.0,
     "items": [{"name": "麦辣鸡腿堡", "quantity": 1}]},
    {"createTime": "2026-09-25", "totalAmount": 38.0,
     "items": [{"name": "麦辣鸡腿堡", "quantity": 1}, {"name": "中可乐", "quantity": 1}]},
    {"createTime": "2026-10-08", "totalAmount": 37.0,
     "items": [{"name": "麦辣鸡腿堡", "quantity": 1}]},
]}
DEMO_POINTS = {"data": {"availablePoint": 1200.0, "currentMouthExpirePoint": 300.0,
                        "nextMouthExpirePoint": 150.0}}
DEMO_MALL = {"data": [
    {"name": "中杯鲜煮咖啡券", "points": 500, "worth": 10.5},
    {"name": "麦辣鸡腿堡券", "points": 3000, "worth": 22.0},
    {"name": "巨无霸中套餐券", "points": 5000, "worth": 39.5},
]}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="silent_cost",
        description="麦麦省钱助手 · 沉默成本体检——临期券排程 + 消费画像 + 积分（数据来自官方 MCP 只读工具）。",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    report = sub.add_parser("report", help="生成体检报告")
    report.add_argument("--coupons", help="query-my-coupons 响应 JSON")
    report.add_argument("--orders", help="order-list 响应 JSON")
    report.add_argument("--points", help="query-my-account 响应 JSON")
    report.add_argument("--mall", help="积分商城商品列表 JSON（用于积分影子价格估算，可选）")
    report.add_argument("--html", metavar="PATH", help="同时输出单文件 HTML 报告（零依赖，可截图分享）")
    report.add_argument("--probe", action="store_true",
                        help="无面值券走 calculate-price 实测精确价值（需要 MCP Token）")
    report.add_argument("--store-code", default="", help="--probe 实测时的门店编码")
    demo = sub.add_parser("demo", help="离线演示（内嵌示例数据）")
    demo.add_argument("--html", metavar="PATH", help="同时输出单文件 HTML 报告（零依赖，可截图分享）")
    return parser


def _run_probe(coupons: Dict[str, Any], store_code: str) -> int:
    """对无面值临期券执行实测；成功则回填 face 并标记 face_source=measured。"""
    try:
        from mcd_client import McdMcpClient, load_token  # 延迟导入，离线路径零依赖
    except ImportError:  # pragma: no cover
        print("错误: 无法导入 mcd_client，请从项目根目录运行。", file=sys.stderr)
        return EXIT_USAGE
    token = load_token()
    if not token:
        print("提示: --probe 需要 MCP Token（MCD_MCP_TOKEN 环境变量），本次跳过实测。",
              file=sys.stderr)
        return EXIT_OK
    client = McdMcpClient(token=token)
    client._store_code = store_code
    client._order_type = 1
    probed = 0
    for coupon in coupons.get("expiring", []):
        if coupon.get("face") is not None:
            continue
        measured = probe_coupon_value(client, coupon)
        if measured is not None:
            coupon["face"] = measured
            coupon["face_source"] = "measured"
            probed += 1
    print("（实测完成：{0} 张券获得精确面值；其余保留估算或标注未识别）".format(probed),
          file=sys.stderr)
    return EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        coupons = analyze_coupons(DEMO_COUPONS, datetime(2026, 10, 12))
        orders = analyze_orders(DEMO_ORDERS, datetime(2026, 10, 12))
        points = analyze_points(DEMO_POINTS)
        schedule = schedule_coupons(coupons, orders)
        print(render_report(coupons, orders, points, analyze_mall(DEMO_MALL), schedule))
        if getattr(args, "html", None):
            _write_html(args.html, coupons, orders, points, schedule)
        return EXIT_OK

    if args.command == "report":
        coupons = analyze_coupons(_load_json(args.coupons) if args.coupons else {})
        orders = analyze_orders(_load_json(args.orders) if args.orders else {})
        points = analyze_points(_load_json(args.points) if args.points else {})
        mall = _load_json(args.mall) if args.mall else None
        if getattr(args, "probe", None):
            code = _run_probe(coupons, getattr(args, "store_code", ""))
            if code != EXIT_OK:
                return code
        schedule = schedule_coupons(coupons, orders)
        print(render_report(coupons, orders, points, analyze_mall(mall), schedule))
        if getattr(args, "html", None):
            _write_html(args.html, coupons, orders, points, schedule)
        return EXIT_OK

    parser.print_help()
    return EXIT_OK


def _write_html(path: str, coupons: Dict[str, Any], orders: Dict[str, Any],
                points: Dict[str, Any], schedule: Optional[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_html(coupons, orders, points, None, schedule))
    print("HTML 报告已生成：{0}（双击打开即可截图分享）".format(path))


if __name__ == "__main__":
    sys.exit(main())
