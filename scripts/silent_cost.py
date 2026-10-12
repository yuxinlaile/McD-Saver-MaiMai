#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦麦省钱助手 —— 沉默成本体检。

回答一个省钱工具很少回答的问题：「你正在白扔多少钱？」

三部分（全部来自官方 MCP 只读工具，零风险）：

- 临期券扫描：7 天内到期的券按面值合计，列出优先处理清单；
- 消费画像：近 N 单的订单数 / 总支出 / 客单价 / 高频复购单品
  （复购 ≥2 次的单品提示改套餐的省钱方向）；
- 积分体检：可用积分与本月/下月即将过期积分。

数据获取（Agent 按 SKILL.md 工作流执行，JSON 原样保存即可）：

    python scripts/mcd.py call query-my-coupons --raw > coupons.json
    python scripts/mcd.py call order-list --raw > orders.json
    python scripts/mcd.py call query-my-account --raw > points.json
    python scripts/silent_cost.py report --coupons coupons.json --orders orders.json \
        --points points.json

解析策略：对每个字段做宽容匹配（常见命名变体 + 标题正则兜底），
识别不到的字段明确标注"未识别"，绝不猜测编造。

示例::

    python scripts/silent_cost.py demo        # 离线演示（内嵌示例数据）

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
            expiring.append({"title": title, "face": face, "days": days})
    expiring.sort(key=lambda c: c["days"])
    return {
        "total": len(records),
        "expiring": expiring,
        "expiring_face_total": sum(c["face"] or 0.0 for c in expiring),
        "unrecognized": unrecognized,
    }


def analyze_orders(orders_raw: Any) -> Dict[str, Any]:
    records = _unwrap(orders_raw)
    amounts: List[float] = []
    item_counter: Dict[str, int] = {}
    unrecognized = 0
    for order in records:
        amount = _parse_amount(_first_key(order, AMOUNT_KEYS))
        if amount is None:
            unrecognized += 1
        else:
            amounts.append(amount)
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
    return {
        "order_count": len(records),
        "amount_count": len(amounts),
        "total_spend": total if amounts else None,
        "avg_ticket": (total / len(amounts)) if amounts else None,
        "top_items": [{"name": n, "count": c} for n, c in top_items if c >= 2],
        "unrecognized": unrecognized,
    }


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


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------
def _fmt(value: Optional[float]) -> str:
    return "¥{0:.2f}".format(value) if value is not None else "未识别"


def render_report(coupons: Dict[str, Any], orders: Dict[str, Any], points: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("=" * 68)
    lines.append("麦麦省钱助手 · 沉默成本体检报告")
    lines.append("=" * 68)

    lines.append("")
    lines.append("【一】临期券（{0} 天内到期）".format(EXPIRING_DAYS))
    if coupons["expiring"]:
        for c in coupons["expiring"]:
            face = "¥{0:.2f}".format(c["face"]) if c["face"] is not None else "面值未识别"
            lines.append("  · {0} ｜ {1} ｜ 还剩 {2} 天".format(c["title"], face, c["days"]))
        lines.append("  合计面值：{0}".format(_fmt(coupons["expiring_face_total"])))
        lines.append("  建议：优先用掉临期券——过期即沉没，凑单达标也比浪费划算。")
    else:
        lines.append("  近 {0} 天内没有临期券。".format(EXPIRING_DAYS))
    if coupons["unrecognized"]:
        lines.append("  （{0} 张券的有效期字段未识别，已跳过）".format(coupons["unrecognized"]))

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
    else:
        lines.append("  积分账户字段未识别（可先用 query-my-account 核对数据）。")
    return "\n".join(lines)


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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="silent_cost",
        description="麦麦省钱助手 · 沉默成本体检——临期券 + 消费画像 + 积分（数据来自官方 MCP 只读工具）。",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    report = sub.add_parser("report", help="生成体检报告")
    report.add_argument("--coupons", help="query-my-coupons 响应 JSON")
    report.add_argument("--orders", help="order-list 响应 JSON")
    report.add_argument("--points", help="query-my-account 响应 JSON")
    sub.add_parser("demo", help="离线演示（内嵌示例数据）")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        print(render_report(analyze_coupons(DEMO_COUPONS, datetime(2026, 10, 12)),
                            analyze_orders(DEMO_ORDERS),
                            analyze_points(DEMO_POINTS)))
        return EXIT_OK

    if args.command == "report":
        coupons = _load_json(args.coupons) if args.coupons else {}
        orders = _load_json(args.orders) if args.orders else {}
        points = _load_json(args.points) if args.points else {}
        print(render_report(analyze_coupons(coupons), analyze_orders(orders), analyze_points(points)))
        return EXIT_OK

    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
