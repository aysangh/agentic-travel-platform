from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # LLM
    model_name: str = "gpt-5-mini"                    
    openai_api_key: SecretStr | None = None

    # Database
    database_url: str
    langgraph_database_url: str | None = None

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    sim_threshold: float | None = None

    # JWT
    jwt_secret_key: str 
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # MCP
    mcp_host: str 
    mcp_port: int
    mcp_server_url: str 

    # Langfuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
