"""产线配置 + ML + 安全边界测试 — T4.1 ~ T4.8
对照 specs/spec.md 5.3.1 / 6.4 / 安全需求
运行: cd specs && pytest test_misc_api.py -v
"""
from conftest import BASE_URL, check_response, make_ingest_payload


class TestProductionLines:
    """产线与工位查询 — T4.1 ~ T4.2"""

    def test_list_lines(self, client):
        """T4.1 获取 3 条产线 + 工位"""
        resp = client.get(f"{BASE_URL}/lines")
        check_response(resp)
        lines = resp.json()["data"]
        assert len(lines) == 3
        codes = {line["code"] for line in lines}
        assert codes == {"LINE-A", "LINE-B", "LINE-C"}
        # 每条产线应有 stations 列表
        for line in lines:
            assert len(line.get("stations", [])) > 0

    def test_list_stations(self, client):
        """T4.2 获取产线 1 的 5 个工位"""
        resp = client.get(f"{BASE_URL}/lines/1/stations")
        check_response(resp)
        assert len(resp.json()["data"]) == 5


class TestMLPlaceholder:
    """ML 模型接口占位 — T4.3 ~ T4.5"""

    def test_ml_models(self, client):
        """T4.3 ML 模型列表 — 返回占位信息"""
        resp = client.get(f"{BASE_URL}/ml/models")
        check_response(resp)
        d = resp.json()["data"]
        assert "models_deployed" in d
        assert "message" in d

    def test_ml_predict(self, client):
        """T4.4 ML 预测 — 返回未来值数组"""
        payload = {"line_id": 1, "metric_name": "temperature", "lookback_minutes": 30}
        resp = client.post(f"{BASE_URL}/ml/predict", json=payload)
        check_response(resp)
        assert len(resp.json()["data"].get("future_values", [])) > 0

    def test_ml_anomaly_detect(self, client):
        """T4.5 ML 异常检测 — 返回 is_anomaly 布尔"""
        resp = client.get(f"{BASE_URL}/ml/anomaly-detect", params={
            "line_id": 1, "metric_name": "temperature", "lookback_minutes": 30,
        })
        check_response(resp)
        assert isinstance(resp.json()["data"].get("is_anomaly"), bool)


class TestSecurityBoundary:
    """安全防护 + 批量边界 — T4.6 ~ T4.8"""

    def test_sql_injection_protection(self, client):
        """T4.6 SQL 注入 — ORM 应转义，不删表"""
        payload = make_ingest_payload(
            {"time": "2026-06-10T15:00:00Z", "line_id": 1,
             "metric_name": "DROP TABLE alarms;--", "metric_value": 1, "unit": "x"},
        )
        resp = client.post(f"{BASE_URL}/data/ingest", json=payload)
        # 不应 500，ORM 会将其作为普通文本入库
        assert resp.status_code == 200

        # 事后验证告警规则列表仍然可访问
        check_resp = client.get(f"{BASE_URL}/alarms/rules")
        assert check_resp.status_code == 200

    def test_xss_protection(self, client):
        """T4.7 XSS 注入 — 作为纯文本存储"""
        payload = make_ingest_payload(
            {"time": "2026-06-10T15:00:00Z", "line_id": 1,
             "metric_name": "<script>alert(1)</script>",
             "metric_value": 1,
             "unit": "<img onerror=alert(1)>"},
        )
        resp = client.post(f"{BASE_URL}/data/ingest", json=payload)
        assert resp.status_code == 200

    def test_bulk_200_points(self, client):
        """T4.8 批量 200 条写入 — 性能边界"""
        points = [
            {"time": "2026-06-10T15:00:00Z", "line_id": 1,
             "metric_name": "temperature", "metric_value": float(i), "unit": "x"}
            for i in range(200)
        ]
        resp = client.post(f"{BASE_URL}/data/ingest", json={"data": points})
        check_response(resp)
        assert resp.json()["data"]["saved"] == 200
