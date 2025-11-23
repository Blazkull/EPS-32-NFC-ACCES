import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Sistema de Acceso NFC Inteligente"
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    CALLMEBOT_API_KEY: str = os.getenv("CALLMEBOT_API_KEY")
    ADMIN_PHONE_NUMBER: str = os.getenv("ADMIN_PHONE_NUMBER")

settings = Settings()