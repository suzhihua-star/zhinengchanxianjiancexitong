"""数据库连接与 Session 管理"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import settings

connect_args = {}
engine_kwargs: dict = {"echo": False}
if settings.DB_MODE == "sqlite":
    connect_args = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 5

engine = create_async_engine(
    settings.database_url, **engine_kwargs, connect_args=connect_args
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite 需要手动启用 WAL 模式 + 外键
        if settings.DB_MODE == "sqlite":
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
