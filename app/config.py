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

    # PASSWORD RESET TOKENS
    reset_token_expire_minutes : int = 60

    # MAIL SERVICE (SANDBOX FOR DEVELOPMENT)
    mail_host     : str = "localhost"               
    mail_port     : int = 587                        
    mail_username : str = ""                        
    mail_password : SecretStr = SecretStr("")       
    mail_from     : str = "noreply@example.com"     
    mail_use_tls  : bool = True   
    
    frontend_url  : str = "http://localhost:8000" # hardcoded for security                  


settings = Settings() # type: ignore[call-arg] # Loaded from .env