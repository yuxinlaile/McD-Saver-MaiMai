"""silent_cost 沉默成本体检单元测试。"""
from datetime import datetime

from silent_cost import (
    analyze_coupons,
    analyze_orders,
    analyze_points,
    render_report,
)

TODAY = datetime(2026, 10, 12)


class TestCoupons:
    def test_expiring_within_window(self):
        raw = {"data": [
            {"title": "满50减12", "parValue": 12.0, "validityEndTime": "2026-10-13 23:59:59"},
            {"title": "远期券", "parValue": 5.0, "validityEndTime": "2026-12-31 23:59:59"},
        ]}
        result = analyze_coupons(raw, TODAY)
        assert result["total"] == 2
        assert len(result["expiring"]) == 1
        assert result["expiring"][0]["days"] == 1
        assert result["expiring_face_total"] == 12.0

    def test_face_fallback_to_title_regex(self):
        raw = [{"title": "满40减10", "endTime": "2026-10-14"}]
        result = analyze_coupons(raw, TODAY)
        assert result["expiring"][0]["face"] == 10.0

    def test_epoch_timestamp(self):
        # 2026-10-15 00:00:00 (本地时区近似，用日期差断言)
        import time
        ts = time.mktime(time.strptime("2026-10-15", "%Y-%m-%d")) * 1000
        result = analyze_coupons([{"title": "T", "expireTime": ts}], TODAY)
        assert 2 <= result["expiring"][0]["days"] <= 4

    def test_unrecognized_skipped(self):
        result = analyze_coupons([{"title": "无日期券"}], TODAY)
        assert result["expiring"] == [] and result["unrecognized"] == 1

    def test_expired_not_listed(self):
        raw = [{"title": "旧券", "parValue": 5.0, "validityEndTime": "2026-09-01"}]
        result = analyze_coupons(raw, TODAY)
        assert result["expiring"] == []


class TestOrders:
    def test_profile_stats(self):
        raw = {"data": [
            {"totalAmount": 30.0, "items": [{"name": "汉堡", "quantity": 1}]},
            {"totalAmount": 40.0, "items": [{"name": "汉堡", "quantity": 1}]},
            {"payable": "¥25.50", "items": [{"name": "可乐"}]},
        ]}
        result = analyze_orders(raw)
        assert result["order_count"] == 3
        assert result["amount_count"] == 3
        assert result["total_spend"] == 95.5
        assert abs(result["avg_ticket"] - 95.5 / 3) < 1e-9
        assert result["top_items"][0] == {"name": "汉堡", "count": 2}

    def test_top_items_excludes_single_purchase(self):
        raw = {"data": [
            {"totalAmount": 1, "items": [{"name": "只点一次"}]},
            {"totalAmount": 1, "items": [{"name": "复购A"}]},
            {"totalAmount": 1, "items": [{"name": "复购A"}]},
        ]}
        result = analyze_orders(raw)
        assert [i["name"] for i in result["top_items"]] == ["复购A"]

    def test_empty(self):
        result = analyze_orders({"data": []})
        assert result["total_spend"] is None and result["top_items"] == []


class TestPoints:
    def test_full_fields(self):
        raw = {"data": {"availablePoint": 130.9, "currentMouthExpirePoint": 0,
                        "nextMouthExpirePoint": 0}}
        result = analyze_points(raw)
        assert result["available"] == 130.9
        assert result["unrecognized"] == 0

    def test_missing(self):
        assert analyze_points({})["unrecognized"] == 1


class TestReport:
    def test_render_contains_sections(self):
        coupons = analyze_coupons({"data": [
            {"title": "满50减12", "parValue": 12.0, "validityEndTime": "2026-10-13 23:59:59"}]},
            TODAY)
        orders = analyze_orders({"data": [
            {"totalAmount": 33.5, "items": [{"name": "麦辣鸡腿堡"}]}]})
        points = analyze_points({"data": {"availablePoint": 100.0}})
        out = render_report(coupons, orders, points)
        assert "临期券" in out and "消费画像" in out and "积分体检" in out

    def test_demo_runs(self, capsys):
        from silent_cost import main
        assert main(["demo"]) == 0
        assert "沉默成本体检报告" in capsys.readouterr().out
