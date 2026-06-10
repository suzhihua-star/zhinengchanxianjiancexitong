"""WebSocket 实时推送路由"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局 WebSocket 连接管理器
active_connections: list[WebSocket] = []


async def broadcast(message: dict) -> None:
    """广播消息到所有连接的客户端"""
    dead: list[WebSocket] = []
    raw = json.dumps(message, ensure_ascii=False)
    for ws in active_connections:
        try:
            await ws.send_text(raw)
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_connections.remove(ws)


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    """实时数据 WebSocket 端点"""
    await ws.accept()
    active_connections.append(ws)
    logger.info("WebSocket 客户端连接: %d 个在线", len(active_connections))

    try:
        # 心跳保活
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30)
                # 客户端发来 pong 或任何消息都忽略
                if data == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # 发送心跳
                try:
                    await ws.send_text(json.dumps({"type": "heartbeat"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket 异常: %s", e)
    finally:
        if ws in active_connections:
            active_connections.remove(ws)
        logger.info("WebSocket 客户端断开: %d 个在线", len(active_connections))
