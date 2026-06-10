"""统计报表模块 API 测试 — T3.1 ~ T3.7
对照 specs/spec.md 5.2.2 / 5.2.3
运行: cd specs && pytest test_stats_api.py -v
"""
from conftest import BASE_URL, check_response


class TestOEE:
    """OEE 设备综合效率 — T3.1 ~ T3.2"""

    def test_oee_calculation(self, client):
        """T3.1 OEE 计算 — 返回三率 + 综合"""
        resp = client.get(f"{BASE_URL}/stats/oee", params={"line_id": 1})
        check_response(resp)
        d = resp.json()["data"]
        assert "oee" in d
        assert "availability" in d
        assert "performance" in d
        assert "quality" in d
        # OEE 应在 [0, 1] 区间
        assert 0 <= d["oee"] <= 1, f"OEE 越界: {d['oee']}"

    def test_oee_nonexistent_line(self, client):
        """T3.2 不存在产线 — 返回 oee=0 不崩溃"""
        resp = client.get(f"{BASE_URL}/stats/oee", params={"line_id": 999})
        check_response(resp)
        assert resp.json()["data"]["oee"] == 0.0


class TestYield:
    """良品率统计 — T3.3"""

    def test_yield_rate(self, client):
        """T3.3 良品率 — 返回计数 + 率"""
        resp = client.get(f"{BASE_URL}/stats/yield", params={"line_id": 1})
        check_response(resp)
        d = resp.json()["data"]
        assert "total_count" in d
        assert "good_count" in d
        assert "defect_count" in d
        assert "yield_rate" in d
        assert 0 <= d["yield_rate"] <= 1


class TestReports:
    """日报 / 周报 / 月报 + CSV 导出 — T3.4 ~ T3.7"""

    def test_daily_report(self, client):
        """T3.4 日报生成 — 按产线"""
        payload = {"report_type": "daily", "line_id": 1}
        resp = client.post(f"{BASE_URL}/reports/generate", json=payload)
        check_response(resp)
        d = resp.json()["data"]
        assert "report_id" in d
        assert d["content"]["report_type"] == "daily"

    def test_weekly_report_all_lines(self, client):
        """T3.5 周报 — 全部产线汇总"""
        payload = {"report_type": "weekly", "line_id": None}
        resp = client.post(f"{BASE_URL}/reports/generate", json=payload)
        check_response(resp)
        content = resp.json()["data"]["content"]
        assert content["report_type"] == "weekly"
        assert "line_summaries" in content

    def test_monthly_report(self, client):
        """T3.6 月报生成"""
        payload = {"report_type": "monthly"}
        resp = client.post(f"{BASE_URL}/reports/generate", json=payload)
        check_response(resp)
        assert resp.json()["data"]["content"]["report_type"] == "monthly"

    def test_csv_export(self, client):
        """T3.7 CSV 导出"""
        payload = {"report_type": "daily"}
        resp = client.post(f"{BASE_URL}/reports/generate/csv", json=payload)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["Content-Type"]
        # CSV 内容应非空
        assert len(resp.text) > 0
        # 应包含表头
        assert "," in resp.text
