from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./app.db"
    upload_dir: str = "./data/uploads"

settings = Settings()

