"""pytest 共用配置 — 智能检测工厂产线系统 API 测试"""
import pytest
import httpx

BASE_URL = "http://localhost:8000/api/v1"


@pytest.fixture(scope="module")
def client():
    """httpx 异步客户端"""
    transport = httpx.HTTPTransport(retries=0)
    with httpx.Client(transport=transport, timeout=httpx.Timeout(10)) as c:
        yield c


@pytest.fixture(scope="module")
def base_url():
    return BASE_URL


def check_response(resp: httpx.Response, expect_code: int = 200, expect_api_code: int = 0):
    """通用响应断言"""
    assert resp.status_code == expect_code, f"HTTP {resp.status_code}: {resp.text[:200]}"
    if expect_code == 200:
        data = resp.json()
        assert data["code"] == expect_api_code, f"api code={data.get('code')}: {data.get('message')}"


def make_ingest_payload(*points: dict) -> dict:
    """快捷构造 ingest 请求体"""
    return {"data": list(points)}
