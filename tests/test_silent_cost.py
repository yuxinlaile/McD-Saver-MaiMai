"""silent_cost 沉默成本体检单元测试。"""
from datetime import datetime

from silent_cost import (
    analyze_coupons,
    analyze_mall,
    analyze_orders,
    analyze_points,
    render_report,
)

TODAY = datetime(2026, 10, 12)
DEMO_POINTS_DATA = {"data": {"availablePoint": 1200.0, "currentMouthExpirePoint": 300.0,
                             "nextMouthExpirePoint": 150.0}}
DEMO_MALL_DATA = {"data": [{"name": "中杯鲜煮咖啡券", "points": 500, "worth": 10.5}]}


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


class TestMallShadowPrice:
    """v1.4.0 新增：积分商城影子价格。"""

    def test_shadow_price_is_max_efficiency(self):
        raw = {"data": [
            {"name": "咖啡券", "points": 500, "worth": 10.5},   # 0.021
            {"name": "套餐券", "points": 5000, "worth": 39.5},  # 0.0079
        ]}
        result = analyze_mall(raw)
        assert result["shadow_price"] == 10.5 / 500
        assert result["best_product"]["name"] == "咖啡券"

    def test_invalid_products_ignored(self):
        result = analyze_mall({"data": [
            {"name": "零分商品", "points": 0, "worth": 10.0},
            {"name": "无面值", "points": 100},
        ]})
        assert result["shadow_price"] is None

    def test_report_includes_shadow_price_line(self):
        from silent_cost import analyze_mall
        mall = analyze_mall({"data": [{"name": "咖啡券", "points": 500, "worth": 10.5}]})
        points = analyze_points({"data": {"availablePoint": 1000.0}})
        out = render_report(analyze_coupons([], TODAY), analyze_orders({"data": []}),
                            points, mall)
        assert "积分价值参考" in out and "0.0210" in out
        assert "¥21.00" in out


class TestCouponSchedule:
    """v1.6.0 新增：用券排程——过期窗口 × 点单频率。"""

    def test_schedule_assigns_by_face_desc(self):
        from silent_cost import analyze_coupons, analyze_orders, schedule_coupons
        coupons = analyze_coupons({"data": [
            {"title": "小券", "parValue": 3.0, "validityEndTime": "2026-10-14"},
            {"title": "大券", "parValue": 10.0, "validityEndTime": "2026-10-17"},
        ]}, today=datetime(2026, 10, 12))
        orders = analyze_orders({"data": [
            {"createTime": "2026-10-10", "totalAmount": 30.0},
            {"createTime": "2026-10-11", "totalAmount": 30.0},
        ]}, today=datetime(2026, 10, 12))
        schedule = schedule_coupons(coupons, orders)
        assert schedule is not None
        # 频率 1 单/天，窗口 2 天 → 2 单 → 两张都排得上
        assert len(schedule["scheduled"]) == 2 and not schedule["missed"]
        assert schedule["scheduled"][0]["title"] == "大券"  # 面值降序优先

    def test_doomed_coupons_sum_matches(self):
        from silent_cost import analyze_coupons, analyze_orders, schedule_coupons
        coupons = analyze_coupons({"data": [
            {"title": "大券", "parValue": 10.0, "validityEndTime": "2026-10-13"},
            {"title": "中券", "parValue": 6.0, "validityEndTime": "2026-10-13"},
            {"title": "小券", "parValue": 3.0, "validityEndTime": "2026-10-13"},
        ]}, today=datetime(2026, 10, 12))
        orders = analyze_orders({"data": [{"createTime": "2026-10-12", "totalAmount": 30.0}]},
                                today=datetime(2026, 10, 12))
        schedule = schedule_coupons(coupons, orders)
        # 窗口 1 天、频率 1 单/天 → 1 单 → 只有 1 张排得上
        assert schedule["expected_orders"] == 1
        assert schedule["scheduled"][0]["face"] == 10.0
        assert abs(schedule["doomed"] - 9.0) < 1e-9
        assert abs(schedule["realizable"] - 10.0) < 1e-9

    def test_no_orders_returns_none(self):
        from silent_cost import analyze_coupons, analyze_orders, schedule_coupons
        coupons = analyze_coupons({"data": [
            {"title": "券", "parValue": 5.0, "validityEndTime": "2026-10-13"}]},
            today=datetime(2026, 10, 12))
        orders = analyze_orders({"data": []}, today=datetime(2026, 10, 12))
        assert schedule_coupons(coupons, orders) is None


class TestProbeCouponValue:
    """v1.6.0 新增：无面值券经 calculate-price 实测，失败返回 None 绝不编造。"""

    class FakeClient:
        def __init__(self, discount):
            self.discount = discount
            self.calls = []
            self._store_code = "ST01"
            self._order_type = 1

        def call_tool(self, name, args):
            self.calls.append((name, args))
            if self.discount is None:
                raise RuntimeError("tool error")
            return {"data": {"discount": self.discount, "payAmount": 20.0}}

    def test_measured_discount_returned(self):
        from silent_cost import probe_coupon_value
        client = self.FakeClient(13.9)
        value = probe_coupon_value(client, {"couponId": "A1", "productCode": "M9"})
        assert value == 13.9
        assert client.calls[0][0] == "calculate-price"
        assert client.calls[0][1]["couponId"] == "A1"

    def test_tool_failure_returns_none(self):
        from silent_cost import probe_coupon_value
        assert probe_coupon_value(self.FakeClient(None), {"couponId": "A1"}) is None

    def test_no_coupon_id_returns_none(self):
        from silent_cost import probe_coupon_value
        assert probe_coupon_value(self.FakeClient(5.0), {"productCode": "M9"}) is None


class TestHtmlReport:
    """v1.6.0 新增：单文件 HTML 报告——零 CDN、可截图分享。"""

    def test_render_html_contains_sections(self):
        from silent_cost import (analyze_coupons, analyze_mall, analyze_orders,
                                 analyze_points, render_html, schedule_coupons)
        coupons = analyze_coupons({"data": [
            {"title": "满30减6", "parValue": 6.0, "validityEndTime": "2026-10-13"}]},
            today=datetime(2026, 10, 12))
        orders = analyze_orders({"data": [{"createTime": "2026-10-01", "totalAmount": 30.0}]},
                                today=datetime(2026, 10, 12))
        html = render_html(coupons, orders, analyze_points(DEMO_POINTS_DATA),
                           analyze_mall(DEMO_MALL_DATA), schedule_coupons(coupons, orders))
        assert "【一】临期券" in html and "【二】消费画像" in html and "【三】积分体检" in html
        assert "注定过期" in html and "maimai-saver" in html
        assert "http://" not in html.replace("http://www.w3.org", "")  # 零外部资源
        assert "<script" not in html  # 无脚本，纯静态
