#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦麦省钱助手 —— 券组合优化器。

确定性枚举「无券直点 / 单券 / 凑单达标」候选方案，按实付价排序输出最优组合
与 Top-N 备选。计价一律交给可插拔的 price_fn：

- 估算模式（默认）：本地用菜单价格与券的 threshold/discount 字段计价，
  输出明确标注「估算模式（本地计价，未经验证）」；
- 真实计价模式（--mcp）：调用官方 calculate-price 逐方案核价，
  结果可作为下单决策依据（延续"不虚构优惠"铁律）。

数据文件（JSON）：

- --wants   想吃清单:    [{"mealCode": "M1", "name": "巨无霸", "quantity": 1}]
- --menu    菜单与价格:  {"storeCode": "...", "orderType": 1,
                          "items": [{"mealCode": "M1", "name": "巨无霸",
                                     "price": 25.0, "category": "汉堡"}]}
- --coupons 可用券:      [{"couponId": "C1", "title": "满40减10",
                            "threshold": 40.0, "discount": 10.0}]

工作流（Agent 按 SKILL.md 执行）：
    query-meals / query-meal-detail  → 写 menu.json（含价格字段）
    query-store-coupons + query-my-coupons → 写 coupons.json（threshold/discount
        从券详情提取；不确定时宁可留空字段走 --mcp 真实计价）
    optimizer.py plan ... [--mcp] → 输出方案排名 → 用户确认后 create-order

示例::

    python scripts/optimizer.py demo                      # 离线演示（内嵌示例数据）
    python scripts/optimizer.py plan --wants wants.json --menu menu.json \
        --coupons coupons.json                          # 估算模式
    python scripts/optimizer.py plan --wants wants.json --menu menu.json \
        --coupons coupons.json --mcp                    # 真实计价模式
    python scripts/optimizer.py plan ... --top 5 --json # Top-N + JSON 输出

退出码：0 成功 · 1 用法/数据错误
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

EXIT_OK = 0
EXIT_USAGE = 1

ADDON_HINT = "（凑单提示：仅当你本来就需要该商品才划算）"

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
class Item:
    def __init__(self, meal_code: str, name: str, price: float, category: str = ""):
        self.meal_code = meal_code
        self.name = name
        self.price = float(price)
        self.category = category

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return "Item({0}, {1})".format(self.meal_code, self.price)


class Cart:
    def __init__(self, entries: List[Dict[str, Any]]):
        # entries: [{"mealCode": ..., "quantity": int}]
        self.entries: List[Dict[str, Any]] = [
            {"mealCode": e["mealCode"], "quantity": max(1, int(e.get("quantity", 1)))}
            for e in entries
        ]

    def with_addon(self, meal_code: str) -> "Cart":
        entries = [dict(e) for e in self.entries]
        for e in entries:
            if e["mealCode"] == meal_code:
                e["quantity"] += 1
                return Cart(entries)
        entries.append({"mealCode": meal_code, "quantity": 1})
        return Cart(entries)

    def item_count(self) -> int:
        return sum(e["quantity"] for e in self.entries)


class Plan:
    def __init__(self, cart: Cart, coupon: Optional[Dict[str, Any]], note: str = ""):
        self.cart = cart
        self.coupon = coupon
        self.note = note
        self.payable: Optional[float] = None
        self.kcal: Optional[float] = None
        self.valid = True
        self.over_budget = False
        self.over_kcal = False

    @property
    def label(self) -> str:
        if self.coupon is None:
            return "无券直点"
        title = self.coupon.get("title") or self.coupon.get("couponId") or "优惠券"
        return str(title)


# ---------------------------------------------------------------------------
# 价格函数
# ---------------------------------------------------------------------------
def make_local_pricer(menu: Dict[str, Any]) -> Callable[[Cart, Optional[Dict[str, Any]]], Optional[float]]:
    """估算模式：本地价格表 + 券 threshold/discount 字段。"""
    price_table = {i["mealCode"]: float(i.get("price", 0) or 0) for i in menu.get("items", [])}

    def price(cart: Cart, coupon: Optional[Dict[str, Any]]) -> Optional[float]:
        face = sum(price_table.get(e["mealCode"], 0.0) * e["quantity"] for e in cart.entries)
        if coupon is None:
            return face
        threshold = float(coupon.get("threshold") or 0.0)
        discount = float(coupon.get("discount") or 0.0)
        if face < threshold:
            return None  # 未达门槛，方案无效
        return max(0.0, face - discount)

    return price


def make_mcp_pricer(client: Any) -> Callable[[Cart, Optional[Dict[str, Any]]], Optional[float]]:
    """真实计价模式：调用官方 calculate-price（含配送费等全部官方规则）。"""

    def price(cart: Cart, coupon: Optional[Dict[str, Any]]) -> Optional[float]:
        args: Dict[str, Any] = {
            "storeCode": getattr(client, "_store_code", ""),
            "orderType": getattr(client, "_order_type", 1),
            "products": [dict(e) for e in cart.entries],
        }
        if coupon and coupon.get("couponId"):
            args["couponId"] = coupon["couponId"]
        result = client.call_tool("calculate-price", args)
        data = result.get("data", result) if isinstance(result, dict) else {}
        for key in ("payable", "totalPay", "payAmount", "payPrice", "total", "totalPrice"):
            value = _dig(data, key)
            if isinstance(value, (int, float)):
                return float(value)
        return None  # 解析不到应付金额时视为无效方案，绝不虚构

    return price


def _dig(obj: Any, key: str) -> Any:
    """在嵌套 dict 中按 key 深度优先查找第一个匹配值。"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _dig(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _dig(v, key)
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------------------
# 候选方案生成与排序
# ---------------------------------------------------------------------------
def build_candidates(
    wants: List[Dict[str, Any]],
    coupons: List[Dict[str, Any]],
    menu: Dict[str, Any],
    addon_limit: int = 3,
) -> List[Plan]:
    """生成候选方案：无券直点 + 每券一方案（未达门槛则尝试最便宜凑单品）
    + 套餐替换（套餐 contains 覆盖全部想吃单品且更省时才会在排名中胜出）。"""
    base = Cart(wants)
    price_table = {i["mealCode"]: float(i.get("price", 0) or 0) for i in menu.get("items", [])}
    face = sum(price_table.get(e["mealCode"], 0.0) * e["quantity"] for e in base.entries)
    wants_codes = {e["mealCode"] for e in base.entries}

    plans: List[Plan] = [Plan(base, None)]
    addons = sorted(
        (i for i in menu.get("items", []) if i["mealCode"] not in wants_codes),
        key=lambda i: float(i.get("price", 0) or 0),
    )[:addon_limit]

    for coupon in coupons:
        threshold = float(coupon.get("threshold") or 0.0)
        if threshold <= 0 or face >= threshold:
            plans.append(Plan(base, coupon))
            continue
        for addon in addons:
            addon_price = float(addon.get("price", 0) or 0)
            if face + addon_price >= threshold:
                plans.append(
                    Plan(base.with_addon(addon["mealCode"]), coupon,
                         note="凑单:{0}".format(addon.get("name", addon["mealCode"])))
                )
                break

    # 套餐替换：套餐 contains 覆盖全部想吃单品时，生成"改点套餐"候选。
    # 是否更省交给计价与排名判断——不预设结论。
    want_qty = {e["mealCode"]: int(e.get("quantity", 1)) for e in base.entries}
    for combo in menu.get("items", []):
        contains = combo.get("contains")
        if not isinstance(contains, list) or combo["mealCode"] in wants_codes:
            continue
        if set(contains) >= wants_codes:
            qty = max(1, max(want_qty.values()))
            swap = Cart([{"mealCode": combo["mealCode"], "quantity": qty}])
            plans.append(Plan(swap, None,
                              note="改点套餐:{0}（覆盖全部想吃单品）".format(combo.get("name", combo["mealCode"]))))
    return plans


def score_and_rank(
    plans: List[Plan],
    price_fn: Callable[[Cart, Optional[Dict[str, Any]]], Optional[float]],
    top: int = 3,
    budget: Optional[float] = None,
    max_kcal: Optional[float] = None,
    kcal_table: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """计价并排序；支持可选约束：实付预算与热量上限。

    违反约束的方案不删除，而是排到满足约束的方案之后并打标——
    用户能看到"差多少"，而不是被静默过滤。
    """
    for plan in plans:
        plan.payable = price_fn(plan.cart, plan.coupon)
        plan.valid = plan.payable is not None
        plan.kcal = None
        if kcal_table and plan.valid:
            kcal = sum(
                kcal_table.get(e["mealCode"], 0.0) * e["quantity"] for e in plan.cart.entries
            )
            plan.kcal = kcal if kcal > 0 else None
            if max_kcal is not None and plan.kcal is not None:
                plan.over_kcal = plan.kcal > max_kcal
        if budget is not None and plan.payable is not None:
            plan.over_budget = plan.payable > budget

    def sort_key(plan: Plan) -> Tuple[float, float, int]:
        violates = (1 if plan.over_budget else 0) + (1 if plan.over_kcal else 0)
        return (violates, plan.payable or 0.0, plan.cart.item_count())

    valid = [p for p in plans if p.valid]
    baseline_candidates = [p for p in valid if p.coupon is None]
    baseline = baseline_candidates[0].payable if baseline_candidates else None
    if baseline is None and valid:
        baseline = min(p.payable for p in valid)

    ranked = sorted(valid, key=sort_key)[: max(1, top)]
    return {"baseline": baseline, "ranked": ranked, "invalid": len(plans) - len(valid),
            "budget": budget, "max_kcal": max_kcal}


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------
def _fmt(value: Optional[float]) -> str:
    return "¥{0:.2f}".format(value) if value is not None else "—"


def render_report(result: Dict[str, Any], mode_label: str) -> str:
    baseline = result["baseline"]
    ranked: List[Plan] = result["ranked"]
    lines: List[str] = []
    lines.append("=" * 68)
    lines.append("麦麦省钱助手 · 最优组合方案（{0}）".format(mode_label))
    lines.append("=" * 68)
    if baseline is None or not ranked:
        lines.append("无可行方案：请检查菜单/券数据，或改用 --mcp 真实计价模式。")
        return "\n".join(lines)

    lines.append("基准（无券直点）：{0}".format(_fmt(baseline)))
    if result.get("budget") is not None:
        lines.append("预算上限：{0}".format(_fmt(result["budget"])))
    if result.get("max_kcal") is not None:
        lines.append("热量上限：{0:.0f} kcal".format(result["max_kcal"]))
    lines.append("")
    lines.append("方案排名：")
    for idx, plan in enumerate(ranked, 1):
        saving = baseline - (plan.payable or 0.0)
        ratio = (saving / baseline * 100.0) if baseline else 0.0
        mark = "  ← 最优" if idx == 1 else ""
        flags = []
        if plan.over_budget:
            flags.append("超预算 {0}".format(_fmt((plan.payable or 0) - (result["budget"] or 0))))
        if plan.over_kcal:
            flags.append("超热量 {0:.0f} kcal".format((plan.kcal or 0) - (result["max_kcal"] or 0)))
        lines.append("  {0}. {1}".format(idx, plan.label))
        kcal_part = " ｜ 热量 {0:.0f} kcal".format(plan.kcal) if plan.kcal is not None else ""
        lines.append("     实付 {0}{1} ｜ 省 {2}（{3:.0f}%）{4}".format(
            _fmt(plan.payable), kcal_part, _fmt(saving), ratio, mark))
        if flags:
            lines.append("     ⚠️ {0}".format("；".join(flags)))
        if plan.note:
            lines.append("     {0}{1}".format(plan.note, ADDON_HINT))
    if result.get("invalid"):
        lines.append("")
        lines.append("（另有 {0} 个候选方案因未达券门槛或计价失败被过滤）".format(result["invalid"]))
    lines.append("")
    lines.append("说明：{0}；最终价格以下单前 calculate-price 返回为准。".format(mode_label))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 演示数据
# ---------------------------------------------------------------------------
DEMO_MENU = {
    "storeCode": "DEMO01", "orderType": 1,
    "items": [
        {"mealCode": "M1", "name": "巨无霸", "price": 25.0, "category": "汉堡", "kcal": 550},
        {"mealCode": "M2", "name": "麦辣鸡腿堡", "price": 22.0, "category": "汉堡", "kcal": 520},
        {"mealCode": "M3", "name": "中薯条", "price": 12.0, "category": "小食", "kcal": 330},
        {"mealCode": "M4", "name": "中可乐", "price": 9.5, "category": "饮品", "kcal": 210},
        {"mealCode": "M5", "name": "麦辣鸡腿堡三件套(堡+中薯+中可)", "price": 33.5,
         "category": "套餐", "kcal": 940, "contains": ["M2", "M3", "M4"]},
        {"mealCode": "M6", "name": "1+1随心配(任选两件)", "price": 13.5, "category": "套餐", "kcal": 480},
        {"mealCode": "M7", "name": "脆薯饼", "price": 7.0, "category": "小食", "kcal": 280},
    ],
}
DEMO_WANTS = [{"mealCode": "M5", "name": "麦辣鸡腿堡三件套", "quantity": 1}]
DEMO_COUPONS = [
    {"couponId": "C3", "title": "满30减6", "threshold": 30.0, "discount": 6.0},
    {"couponId": "C1", "title": "到店取餐9折券", "threshold": 0.0, "discount": 3.35},
    {"couponId": "C2", "title": "满40减10", "threshold": 40.0, "discount": 10.0},
]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="optimizer",
        description="麦麦省钱助手 · 券组合优化器——枚举候选方案，真实/估算计价，输出最优组合。",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    plan = sub.add_parser("plan", help="生成并排序候选方案")
    plan.add_argument("--wants", required=True, help="想吃清单 JSON 文件")
    plan.add_argument("--menu", required=True, help="菜单与价格 JSON 文件")
    plan.add_argument("--coupons", required=True, help="可用券 JSON 文件")
    plan.add_argument("--mcp", action="store_true",
                      help="真实计价模式：调用官方 calculate-price（需要 MCP Token）")
    plan.add_argument("--store-code", default="", help="真实计价模式必填：门店编码")
    plan.add_argument("--order-type", type=int, default=1, help="1=到店(默认) 2=外送")
    plan.add_argument("--top", type=int, default=3, help="输出前 N 个方案（默认 3）")
    plan.add_argument("--budget", type=float, default=None, help="实付预算上限（元），超支方案排后并打标")
    plan.add_argument("--max-kcal", type=float, default=None, help="热量上限（kcal），菜单含 kcal 字段时生效")
    plan.add_argument("--json", dest="as_json", action="store_true", help="JSON 输出")

    sub.add_parser("demo", help="离线演示（内嵌示例数据，估算模式）")
    return parser


def run_plan(args: argparse.Namespace) -> int:
    try:
        wants = _load_json(args.wants)
        menu = _load_json(args.menu)
        coupons = _load_json(args.coupons)
    except (OSError, json.JSONDecodeError) as exc:
        print("错误: 无法读取数据文件：{0}".format(exc), file=sys.stderr)
        return EXIT_USAGE
    if not isinstance(wants, list) or not isinstance(menu, dict) or not isinstance(coupons, list):
        print("错误: 数据文件结构不正确（wants/coupons 应为数组，menu 应为对象）。", file=sys.stderr)
        return EXIT_USAGE

    if args.mcp:
        try:
            from mcd_client import McdMcpClient, load_token  # 延迟导入，估算模式零依赖
        except ImportError:  # pragma: no cover - 路径异常时提示
            print("错误: 无法导入 mcd_client，请从项目根目录运行。", file=sys.stderr)
            return EXIT_USAGE
        token = load_token()
        if not token:
            print("错误: 真实计价模式需要 MCP Token（MCD_MCP_TOKEN 环境变量）。", file=sys.stderr)
            return EXIT_USAGE
        client = McdMcpClient(token=token)
        client._store_code = args.store_code or menu.get("storeCode", "")
        client._order_type = args.order_type or menu.get("orderType", 1)
        price_fn = make_mcp_pricer(client)
        mode_label = "真实计价模式（官方 calculate-price）"
    else:
        price_fn = make_local_pricer(menu)
        mode_label = "估算模式（本地计价，未经验证）"

    plans = build_candidates(wants, coupons, menu)
    kcal_table = {i["mealCode"]: float(i["kcal"]) for i in menu.get("items", [])
                  if isinstance(i.get("kcal"), (int, float))}
    result = score_and_rank(plans, price_fn, top=args.top,
                            budget=args.budget,
                            max_kcal=args.max_kcal if kcal_table else None,
                            kcal_table=kcal_table or None)

    if args.as_json:
        print(json.dumps({
            "mode": "mcp" if args.mcp else "estimate",
            "baseline": result["baseline"],
            "plans": [
                {"label": p.label, "payable": p.payable, "note": p.note,
                 "saving": (result["baseline"] - p.payable) if result["baseline"] and p.payable else None,
                 "cart": p.cart.entries}
                for p in result["ranked"]
            ],
            "filtered": result["invalid"],
        }, ensure_ascii=False, indent=2))
    else:
        print(render_report(result, mode_label))
    return EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "plan":
        return run_plan(args)
    if args.command == "demo":
        plans = build_candidates(DEMO_WANTS, DEMO_COUPONS, DEMO_MENU)
        kcal_table = {i["mealCode"]: float(i["kcal"]) for i in DEMO_MENU["items"]}
        result = score_and_rank(plans, make_local_pricer(DEMO_MENU), top=3,
                                kcal_table=kcal_table)
        print(render_report(result, "估算模式（本地计价，未经验证）"))
        return EXIT_OK
    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
