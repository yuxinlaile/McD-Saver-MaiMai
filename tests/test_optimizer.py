"""optimizer 券组合优化器单元测试。"""
import pytest

from optimizer import (
    Cart,
    build_candidates,
    make_local_pricer,
    score_and_rank,
)

MENU = {
    "storeCode": "T01", "orderType": 1,
    "items": [
        {"mealCode": "A", "name": "主餐", "price": 25.0},
        {"mealCode": "B", "name": "小食", "price": 12.0},
        {"mealCode": "C", "name": "凑单品", "price": 7.0},
        {"mealCode": "D", "name": "贵凑单", "price": 20.0},
    ],
}
WANTS = [{"mealCode": "A", "quantity": 1}]  # 面值 25.0
COUPONS = [
    {"couponId": "C1", "title": "满25减6", "threshold": 25.0, "discount": 6.0},
    {"couponId": "C2", "title": "满40减10", "threshold": 40.0, "discount": 10.0},
]


class TestLocalPricer:
    def test_no_coupon_returns_face(self):
        price = make_local_pricer(MENU)
        assert price(Cart(WANTS), None) == 25.0

    def test_below_threshold_invalid(self):
        price = make_local_pricer(MENU)
        assert price(Cart(WANTS), COUPONS[1]) is None  # 25 < 40

    def test_threshold_boundary_valid(self):
        price = make_local_pricer(MENU)
        assert price(Cart(WANTS), COUPONS[0]) == 19.0  # 25 - 6

    def test_discount_capped_at_zero(self):
        menu = {"items": [{"mealCode": "A", "price": 5.0}]}
        price = make_local_pricer(menu)
        assert price(Cart(WANTS), {"threshold": 0, "discount": 100.0}) == 0.0


class TestCandidateGeneration:
    def test_always_includes_baseline(self):
        plans = build_candidates(WANTS, [], MENU)
        assert len(plans) == 1 and plans[0].coupon is None

    def test_addon_is_cheapest_sufficient(self):
        plans = build_candidates(WANTS, COUPONS, MENU)
        addon_plan = [p for p in plans if p.note.startswith("凑单")]
        assert len(addon_plan) == 1
        # 25 + 7(C) = 32 仍不达 40；只有 +20(D) 达标 → 选 D
        assert "贵凑单" in addon_plan[0].note

    def test_no_addon_when_threshold_reachable(self):
        plans = build_candidates(WANTS, [COUPONS[0]], MENU)
        assert all(not p.note for p in plans)

    def test_zero_threshold_coupon_no_addon(self):
        coupons = [{"couponId": "C0", "title": "无门槛", "threshold": 0.0, "discount": 2.0}]
        plans = build_candidates(WANTS, coupons, MENU)
        assert len(plans) == 2 and all(not p.note for p in plans)


class TestRanking:
    def _rank(self, wants=WANTS, coupons=COUPONS):
        plans = build_candidates(wants, coupons, MENU)
        return score_and_rank(plans, make_local_pricer(MENU), top=3)

    def test_best_plan_is_cheapest(self):
        result = self._rank()
        assert result["ranked"][0].payable == min(p.payable for p in result["ranked"])

    def test_baseline_is_no_coupon(self):
        result = self._rank()
        assert result["baseline"] == 25.0

    def test_tie_prefers_fewer_items(self):
        menu = {"items": [
            {"mealCode": "A", "price": 30.0},
            {"mealCode": "E", "price": 0.0},
        ]}
        coupons = [{"couponId": "X", "title": "满30减10", "threshold": 30.0, "discount": 10.0}]
        plans = build_candidates([{"mealCode": "A"}], coupons, menu)
        result = score_and_rank(plans, make_local_pricer(menu))
        # 30-10=20（2 件）与 30+0-10=20（3 件）同价时，少件者优先
        assert result["ranked"][0].cart.item_count() == 1

    def test_saving_math(self):
        result = self._rank()
        best = result["ranked"][0]
        assert abs((result["baseline"] - best.payable) - 6.0) < 1e-9


class TestCliSmoke:
    def test_demo_runs(self, capsys):
        from optimizer import main
        assert main(["demo"]) == 0
        out = capsys.readouterr().out
        assert "最优组合方案" in out and "凑单" in out

    def test_plan_requires_files(self):
        from optimizer import main
        assert main(["plan", "--wants", "nope.json", "--menu", "nope.json",
                     "--coupons", "nope.json"]) == 1


class TestConstraints:
    """v1.4.0 新增：热量/预算约束与套餐替换。"""

    MENU_KCAL = {"items": [
        {"mealCode": "A", "name": "主餐", "price": 25.0, "kcal": 550},
        {"mealCode": "B", "name": "小食", "price": 12.0, "kcal": 330},
        {"mealCode": "M", "name": "主餐套餐(含主餐)", "price": 23.0,
         "kcal": 520, "contains": ["A"]},
    ]}

    def test_kcal_computed_per_plan(self):
        plans = build_candidates(WANTS, [], self.MENU_KCAL)
        result = score_and_rank(plans, make_local_pricer(self.MENU_KCAL),
                                kcal_table={"A": 550.0, "M": 520.0})
        assert result["ranked"][0].kcal == 520.0  # 排名第一的是改点套餐方案

    def test_budget_flags_over_budget(self):
        plans = build_candidates(WANTS, [], MENU)
        result = score_and_rank(plans, make_local_pricer(MENU), budget=20.0)
        assert all(p.over_budget for p in result["ranked"] if (p.payable or 0) > 20.0)

    def test_over_kcal_ranked_last(self):
        plans = build_candidates(WANTS, [], self.MENU_KCAL)
        result = score_and_rank(plans, make_local_pricer(self.MENU_KCAL),
                                max_kcal=400, kcal_table={"A": 550})
        assert result["ranked"][-1].over_kcal

    def test_set_meal_swap_candidate(self):
        # wants=[主餐]，菜单里存在 contains 覆盖 A 的套餐 → 生成改点套餐候选
        plans = build_candidates([{"mealCode": "A"}], [], self.MENU_KCAL)
        swaps = [p for p in plans if p.note.startswith("改点套餐")]
        assert len(swaps) == 1
        assert swaps[0].cart.entries[0]["mealCode"] == "M"

    def test_swap_priced_cheaper_and_wins(self):
        # 套餐 23 元 < 单点 25 元 → 排名第一（改点套餐方案为无券，标签同基准）
        plans = build_candidates([{"mealCode": "A"}], [], self.MENU_KCAL)
        result = score_and_rank(plans, make_local_pricer(self.MENU_KCAL))
        assert result["ranked"][0].payable == 23.0
        assert result["ranked"][0].note.startswith("改点套餐")

    def test_swap_skipped_when_combo_is_want(self):
        plans = build_candidates([{"mealCode": "M"}], [], self.MENU_KCAL)
        assert all(not p.note.startswith("改点套餐") for p in plans)
