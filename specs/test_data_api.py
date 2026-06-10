"""数据采集模块 API 测试 — T1.1 ~ T1.13
对照 specs/spec.md 5.1 / 5.2.3
运行: cd specs && pytest test_data_api.py -v
"""
import pytest
from conftest import BASE_URL, check_response, make_ingest_payload


class TestDataIngest:
    """POST /api/v1/data/ingest — 传感器数据写入"""

    def test_normal_write(self, client):
        """T1.1 正常写入 2 条传感器数据"""
        payload = make_ingest_payload(
            {"time": "2026-06-10T15:00:00Z", "line_id": 1, "station_id": 1,
             "metric_name": "temperature", "metric_value": 150.5, "unit": "℃"},
            {"time": "2026-06-10T15:00:00Z", "line_id": 1, "station_id": 1,
             "metric_name": "humidity", "metric_value": 45.0, "unit": "%RH"},
        )
        resp = client.post(f"{BASE_URL}/data/ingest", json=payload)
        check_response(resp)
        assert resp.json()["data"]["saved"] == 2

    def test_empty_array(self, client):
        """T1.2 空数组写入 — 应返回 saved=0"""
        resp = client.post(f"{BASE_URL}/data/ingest", json={"data": []})
        check_response(resp)
        assert resp.json()["data"]["saved"] == 0

    def test_missing_required_field(self, client):
        """T1.3 缺少必填字段 metric_name — 应返回 422"""
        payload = {"data": [{"line_id": 1, "metric_value": 100}]}
        resp = client.post(f"{BASE_URL}/data/ingest", json=payload)
        assert resp.status_code == 422

    def test_negative_value(self, client):
        """T1.4 负数数值 — 应正常入库（负压等场景合法）"""
        payload = make_ingest_payload(
            {"time": "2026-06-10T15:01:00Z", "line_id": 1, "station_id": 1,
             "metric_name": "pressure", "metric_value": -10, "unit": "MPa"},
        )
        resp = client.post(f"{BASE_URL}/data/ingest", json=payload)
        check_response(resp)
        assert resp.json()["data"]["saved"] == 1

    def test_nonexistent_line(self, client):
        """T1.5 不存在的产线 — 宽松入库不拒绝"""
        payload = make_ingest_payload(
            {"time": "2026-06-10T15:01:00Z", "line_id": 999, "station_id": 999,
             "metric_name": "temperature", "metric_value": 99999.99, "unit": "℃"},
        )
        resp = client.post(f"{BASE_URL}/data/ingest", json=payload)
        check_response(resp)
        assert resp.json()["data"]["saved"] == 1


class TestDataLatest:
    """GET /api/v1/data/latest — 最新传感器数据"""

    def test_latest_all(self, client):
        """T1.6 获取全部最新数据"""
        resp = client.get(f"{BASE_URL}/data/latest")
        check_response(resp)
        assert len(resp.json()["data"]) > 0

    def test_latest_by_line(self, client):
        """T1.7 按产线筛选"""
        resp = client.get(f"{BASE_URL}/data/latest", params={"line_id": 1})
        check_response(resp)
        for item in resp.json()["data"]:
            assert item["line_id"] == 1

    def test_latest_nonexistent_line(self, client):
        """T1.8 不存在产线 — 返回空数组或正常 JSON"""
        resp = client.get(f"{BASE_URL}/data/latest", params={"line_id": 999})
        assert resp.status_code in (200, 404)


class TestDataHistory:
    """GET /api/v1/data/history — 历史数据分页"""

    def test_history_default(self, client):
        """T1.9 无参数 — 默认最多 500 条"""
        resp = client.get(f"{BASE_URL}/data/history")
        check_response(resp)
        assert len(resp.json()["data"]) <= 500

    def test_history_limit_one(self, client):
        """T1.10 limit=1"""
        resp = client.get(f"{BASE_URL}/data/history", params={"limit": 1})
        check_response(resp)
        assert len(resp.json()["data"]) == 1

    def test_history_limit_exceed(self, client):
        """T1.11 limit 超限 — 422"""
        resp = client.get(f"{BASE_URL}/data/history", params={"limit": 2001})
        assert resp.status_code == 422


class TestDataTrend:
    """GET /api/v1/data/trend + POST /api/v1/data/comparison"""

    def test_trend_minute_aggregation(self, client):
        """T1.12 分钟聚合趋势"""
        resp = client.get(f"{BASE_URL}/data/trend", params={
            "line_id": 1, "metric_name": "temperature", "minutes": 10,
        })
        check_response(resp)
        assert isinstance(resp.json()["data"], list)

    def test_comparison(self, client):
        """T1.13 多产线对比趋势"""
        payload = {"line_ids": [1, 2], "metric_name": "temperature", "minutes": 30}
        resp = client.post(f"{BASE_URL}/data/comparison", json=payload)
        check_response(resp)
        assert len(resp.json()["data"]) >= 1
