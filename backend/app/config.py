from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Modu Backend"
    debug: bool = False

    database_url: str = "postgresql+psycopg2://modu:modu@localhost:5432/modu"
    redis_url: str = "redis://localhost:6379/0"

    upload_max_size_bytes: int = 100 * 1024 * 1024  # 100MB
    upload_chunk_size_bytes: int = 5 * 1024 * 1024  # 5MB
    upload_storage_path: str = "/data/uploads"

    allowed_file_extensions: set[str] = {
        ".pdf", ".docx", ".xlsx", ".pptx", ".ppt",
        ".txt", ".jpg", ".jpeg", ".png", ".tiff", ".tif",
    }

    allowed_mime_types: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "image/jpeg",
        "image/png",
        "image/tiff",
    }

    # LLM configuration
    llm_provider: str = "mock"  # "mock" or "litellm"
    llm_model: str = "kimi-k2-6"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.moonshot.cn/v1"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 8192

    # Code generation configuration
    code_template_version: str = "1.0.0"
    code_naming_convention: str = "mixed"  # "mixed" | "camelCase" | "snake_case"
    code_author_default: str = "AI_Generated"

    # ASIL configuration
    code_asil_safety_mechanisms: bool = True
    asil_coverage_targets: dict = {
        "A": {"statement": 80, "branch": 70},
        "B": {"statement": 90, "branch": 80, "mcdc": 50},
        "C": {"statement": 95, "branch": 90, "mcdc": 70},
        "D": {"statement": 95, "branch": 90, "mcdc": 70},
    }


settings = Settings()
