"""All settings come from environment variables (or a .env file in backend/)."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.env = os.getenv("ENV", "development")                  # development | production
        self.database_url = os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eatfit")
        self.auth_mode = os.getenv("AUTH_MODE", "dev")               # dev | supabase
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "")  # only for legacy HS256 projects
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")  # server-only secret
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
        self.max_upload_mb = float(os.getenv("MAX_UPLOAD_MB", "6"))

        if self.env == "production" and self.auth_mode != "supabase":
            raise RuntimeError("Refusing to start: production must use AUTH_MODE=supabase")


settings = Settings()
