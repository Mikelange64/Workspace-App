from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR /".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    database_url : str = "postgresql://localhost/workspaceapp_db"

    # JWT INFO
    secret_key : SecretStr
    algorithm : str = "HS256"
    access_token_expire_minutes : int = 30

    # AWS S3 BUCKET INFO
    s3_bucket_name       : str
    s3_region            : str = "us-east-2"
    s3_access_key_id     : SecretStr | None = None
    s3_secret_access_key : SecretStr | None = None
    s3_endpoint_url      : str | None = None

    # PROFILE PIC UPLOAD INFO
    max_upload_size_bytes: int = 5 * 1024 * 1024

    # FILE UPLOAD INFO
    max_file_upload_size_bytes: int = 30 * 1024 * 1024

    # PASSWORD RESET TOKENS
    reset_token_expire_minutes  : int = 60

    # REFRESH TOKENS
    refresh_token_expire_days : int = 7

    # MAIL SERVICE (RESEND FOR DEPLOYMENT)
    mail_host     : str = "localhost"               
    mail_port     : int = 465                        
    mail_username : str = ""                        
    mail_password : SecretStr = SecretStr("")       
    mail_from     : str = "noreply@filobelo.com"     
    mail_use_tls  : bool = True   
    
    cors_origins  : list[str] = ["http://localhost:5173"]

    frontend_url  : str = "http://localhost:5173" # hardcoded for security


settings = Settings() # type: ignore[call-arg] # Loaded from .env