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


settings = Settings()
