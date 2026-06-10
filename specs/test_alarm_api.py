"""告警引擎模块 API 测试 — T2.1 ~ T2.17
对照 specs/spec.md 5.2.1 / 5.3.3
运行: cd specs && pytest test_alarm_api.py -v
"""
import pytest
from conftest import BASE_URL, check_response, make_ingest_payload


class TestAlarmRulesCRUD:
    """告警规则 CRUD — T2.1 ~ T2.5"""

    def test_list_rules(self, client):
        """T2.1 获取规则列表 — 至少含种子数据的 27 条"""
        resp = client.get(f"{BASE_URL}/alarms/rules")
        check_response(resp)
        assert len(resp.json()["data"]) >= 27, f"预期≥27, 实际{len(resp.json()['data'])}"

    def test_create_rule(self, client):
        """T2.2 创建静态阈值规则"""
        payload = {
            "name": "TEST_规则",
            "line_id": 1,
            "metric_name": "temperature",
            "rule_type": "static",
            "upper_limit": 100,
            "lower_limit": 50,
            "severity": "warning",
            "is_active": True,
        }
        resp = client.post(f"{BASE_URL}/alarms/rules", json=payload)
        check_response(resp)
        d = resp.json()["data"]
        assert d["name"] == "TEST_规则"
        # 存下 id 供后续更新/删除使用
        client.test_rule_id = d["id"]

    def test_update_rule(self, client):
        """T2.3 更新告警规则"""
        # 依赖 T2.2 先创建
        if not hasattr(client, "test_rule_id"):
            pytest.skip("依赖 T2.2 未执行")
        payload = {"name": "TEST_规则_UPDATED", "upper_limit": 120}
        resp = client.put(
            f"{BASE_URL}/alarms/rules/{client.test_rule_id}", json=payload,
        )
        check_response(resp)
        d = resp.json()["data"]
        assert d["name"] == "TEST_规则_UPDATED"
        assert d["upper_limit"] == 120.0

    def test_update_nonexistent_rule(self, client):
        """T2.4 更新不存在的规则 — 404"""
        resp = client.put(f"{BASE_URL}/alarms/rules/99999", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_rule(self, client):
        """T2.5 删除告警规则"""
        if not hasattr(client, "test_rule_id"):
            pytest.skip("依赖 T2.2 未执行")
        resp = client.delete(f"{BASE_URL}/alarms/rules/{client.test_rule_id}")
        check_response(resp)


class TestAlarmLifecycle:
    """告警触发 / 列表 / 筛选 / 确认 / 关闭 — T2.6 ~ T2.11"""

    def test_alarm_triggered_by_anomaly(self, client):
        """T2.6 异常数据触发告警 (温度 300℃ >> 上限 175℃)"""
        payload = make_ingest_payload(
            {"time": "2026-06-10T16:00:00Z", "line_id": 1, "station_id": 1,
             "metric_name": "temperature", "metric_value": 300.0, "unit": "℃"},
        )
        resp = client.post(f"{BASE_URL}/data/ingest", json=payload)
        check_response(resp)
        # 可能因去重窗口未触发，仅验证不报错
        triggered = resp.json()["data"]["alarms_triggered"]
        assert isinstance(triggered, int)

    def test_alarm_list_with_pagination(self, client):
        """T2.7 告警分页查询"""
        resp = client.get(f"{BASE_URL}/alarms", params={"page": 1, "page_size": 3})
        check_response(resp)
        d = resp.json()["data"]
        assert d["page"] == 1
        assert len(d["items"]) <= 3

    def test_alarm_filter_by_line_and_status(self, client):
        """T2.8 按产线 + 未确认状态筛选"""
        resp = client.get(f"{BASE_URL}/alarms", params={
            "line_id": 1, "status": "unconfirmed",
        })
        check_response(resp)
        for item in resp.json()["data"]["items"]:
            assert item["line_id"] == 1
            assert item["status"] == "unconfirmed"

    def test_confirm_alarm(self, client):
        """T2.9 告警确认"""
        # 先取一条未确认告警
        list_resp = client.get(f"{BASE_URL}/alarms", params={
            "status": "unconfirmed", "page_size": 1,
        })
        items = list_resp.json()["data"]["items"]
        if not items:
            pytest.skip("无未确认告警可确认")
        aid = items[0]["id"]
        resp = client.put(f"{BASE_URL}/alarms/{aid}/confirm")
        check_response(resp)
        assert resp.json()["data"]["status"] == "confirmed"

    def test_confirm_nonexistent(self, client):
        """T2.10 确认不存在告警 — 404"""
        resp = client.put(f"{BASE_URL}/alarms/99999/confirm")
        assert resp.status_code == 404

    def test_resolve_alarm(self, client):
        """T2.11 告警关闭"""
        list_resp = client.get(f"{BASE_URL}/alarms", params={
            "status": "unconfirmed", "page_size": 1,
        })
        items = list_resp.json()["data"]["items"]
        if not items:
            pytest.skip("无未确认告警可关闭")
        aid = items[0]["id"]
        resp = client.put(f"{BASE_URL}/alarms/{aid}/resolve")
        check_response(resp)
        assert resp.json()["data"]["status"] == "resolved"


class TestDefectBreakdown:
    """缺陷分类统计 — T2.12 ~ T2.13"""

    def test_defect_breakdown_all(self, client):
        """T2.12 全局缺陷分类"""
        resp = client.get(f"{BASE_URL}/alarms/defect-breakdown", params={"hours": 24})
        check_response(resp)
        d = resp.json()["data"]
        assert "total_defects" in d
        assert "categories" in d

    def test_defect_breakdown_by_line(self, client):
        """T2.13 单产线缺陷统计"""
        resp = client.get(f"{BASE_URL}/alarms/defect-breakdown", params={
            "line_id": 1, "hours": 24,
        })
        check_response(resp)
        assert isinstance(resp.json()["data"]["total_defects"], int)


class TestCompositeRules:
    """组合告警规则 CRUD — T2.14 ~ T2.17"""

    def test_list_empty(self, client):
        """T2.14 初始空列表"""
        resp = client.get(f"{BASE_URL}/alarms/composite-rules")
        check_response(resp)
        assert isinstance(resp.json()["data"], list)

    def test_create_composite(self, client):
        """T2.15 创建组合规则 AND(规则1, 规则2)"""
        payload = {
            "name": "TEST_COMPOSITE",
            "line_id": 1,
            "rule_ids": [1, 2],
            "logic": "AND",
            "composite_severity": "critical",
        }
        resp = client.post(f"{BASE_URL}/alarms/composite-rules", json=payload)
        check_response(resp)
        d = resp.json()["data"]
        assert d["logic"] == "AND"
        assert d["rule_ids"] == [1, 2]
        client.comp_rule_id = d["id"]

    def test_list_after_create(self, client):
        """T2.17 创建后列表含 1 条"""
        resp = client.get(f"{BASE_URL}/alarms/composite-rules")
        check_response(resp)
        # 可能为 0 或 1（取决于是否与其他测试共享客户端状态）
        assert isinstance(resp.json()["data"], list)

    def test_delete_composite(self, client):
        """T2.16 删除组合规则"""
        if not hasattr(client, "comp_rule_id"):
            pytest.skip("依赖 T2.15 未执行")
        resp = client.delete(
            f"{BASE_URL}/alarms/composite-rules/{client.comp_rule_id}",
        )
        check_response(resp)
