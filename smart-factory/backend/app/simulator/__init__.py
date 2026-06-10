"""产线模拟数据生成器 - 独立进程运行"""
import asyncio
import logging
import random
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# 食品/药品包装产线模拟配置
LINE_CONFIGS = [
    {
        "line_id": 1,
        "stations": [
            {"station_id": 1, "name": "上料工位"},
            {"station_id": 2, "name": "热封工位"},
            {"station_id": 3, "name": "检测工位"},
            {"station_id": 4, "name": "喷码工位"},
            {"station_id": 5, "name": "装箱工位"},
        ],
        "metrics": {
            "temperature": {"base": 155.0, "noise": 3.0, "unit": "℃"},
            "humidity": {"base": 45.0, "noise": 2.0, "unit": "%RH"},
            "pressure": {"base": 0.75, "noise": 0.05, "unit": "MPa"},
            "speed": {"base": 1.2, "noise": 0.1, "unit": "m/s"},
        },
    },
    {
        "line_id": 2,
        "stations": [
            {"station_id": 1, "name": "上料工位"},
            {"station_id": 2, "name": "充填工位"},
            {"station_id": 3, "name": "热封工位"},
            {"station_id": 4, "name": "检测工位"},
        ],
        "metrics": {
            "temperature": {"base": 160.0, "noise": 2.5, "unit": "℃"},
            "humidity": {"base": 50.0, "noise": 1.5, "unit": "%RH"},
            "pressure": {"base": 0.80, "noise": 0.04, "unit": "MPa"},
            "speed": {"base": 1.0, "noise": 0.08, "unit": "m/s"},
        },
    },
    {
        "line_id": 3,
        "stations": [
            {"station_id": 1, "name": "上料工位"},
            {"station_id": 2, "name": "成型工位"},
            {"station_id": 3, "name": "热封工位"},
            {"station_id": 4, "name": "冷却工位"},
            {"station_id": 5, "name": "检测工位"},
        ],
        "metrics": {
            "temperature": {"base": 148.0, "noise": 3.5, "unit": "℃"},
            "humidity": {"base": 42.0, "noise": 1.8, "unit": "%RH"},
            "pressure": {"base": 0.72, "noise": 0.06, "unit": "MPa"},
            "speed": {"base": 1.15, "noise": 0.12, "unit": "m/s"},
        },
    },
]


def generate_metric_value(base: float, noise: float, anomaly_rate: float) -> float:
    """生成带噪声和随机异常注入的指标值"""
    if random.random() < anomaly_rate:
        # 异常注入：大幅偏离基准值
        direction = random.choice([-1, 1])
        anomaly_factor = random.uniform(0.15, 0.35)
        return base + direction * base * anomaly_factor

    return base + random.gauss(0, noise)


async def simulate_lines(backend_url: str, interval: float, anomaly_rate: float) -> None:
    """主模拟循环"""
    logger.info("模拟器启动, 后端地址=%s, 间隔=%.1fs, 异常率=%.1f%%", backend_url, interval, anomaly_rate * 100)

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        while True:
            try:
                data_batch: list[dict] = []
                now = datetime.now(timezone.utc)

                for line_config in LINE_CONFIGS:
                    for station in line_config["stations"]:
                        for metric_name, metric_config in line_config["metrics"].items():
                            value = generate_metric_value(
                                metric_config["base"],
                                metric_config["noise"],
                                anomaly_rate,
                            )
                            data_batch.append(
                                {
                                    "time": now.isoformat(),
                                    "line_id": line_config["line_id"],
                                    "station_id": station["station_id"],
                                    "metric_name": metric_name,
                                    "metric_value": round(value, 2),
                                    "unit": metric_config["unit"],
                                }
                            )

                resp = await client.post(
                    f"{backend_url}/api/v1/data/ingest", json={"data": data_batch}
                )
                if resp.status_code != 200:
                    logger.warning("数据推送失败: HTTP %d", resp.status_code)

                logger.debug("推送 %d 条数据成功", len(data_batch))
            except Exception as e:
                logger.error("模拟器异常: %s", e)

            await asyncio.sleep(interval)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [simulator] %(message)s",
    )

    backend_url = os.getenv("SIMULATOR_BACKEND_URL", "http://localhost:8000")
    interval = float(os.getenv("SIMULATOR_INTERVAL", "1.0"))
    anomaly_rate = float(os.getenv("SIMULATOR_ANOMALY_RATE", "0.03"))

    asyncio.run(simulate_lines(backend_url, interval, anomaly_rate))


if __name__ == "__main__":
    main()
