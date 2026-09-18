from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/app/config.py 向上两级），.env 位于根目录
ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    dashscope_api_key: str
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"
    embedding_model: str = "text-embedding-v3"
    # RAG 检索余弦距离阈值（pgvector <=>）：大于该值视为不相关，不进 prompt
    rag_distance_threshold: float = 0.5
    auth_secret: str

    # MySQL 订单数据源（只读）。host/user/database 三项齐全才启用订单工具，缺省=功能关闭
    mysql_host: str = ""
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = ""


settings = Settings()
