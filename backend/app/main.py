from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import close_pool
from .mysql import close_pool as close_mysql_pool
from .routers import chat, config, conversations, documents, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()
    await close_mysql_pool()


app = FastAPI(title="AI Chat Backend", lifespan=lifespan)

# 开发期允许跨域；浏览器侧同域经 Next rewrites 转发，CORS 仅兜底直连场景
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(config.router)
app.include_router(conversations.router)
app.include_router(documents.router)
