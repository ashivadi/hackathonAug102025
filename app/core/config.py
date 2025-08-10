from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load environment variables from .env into process environment
# This must happen before we access os.getenv()
load_dotenv()


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./assistant.db")
    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    default_tz: str = os.getenv("DEFAULT_TZ", "America/Los_Angeles")
    enable_scheduler: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"

    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "")
    google_scopes: str = os.getenv(
        "GOOGLE_SCOPES", "https://www.googleapis.com/auth/calendar"
    )


settings = Settings()
