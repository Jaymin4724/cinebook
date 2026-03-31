from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    DB_URL: str
    TEST_DB_URL: str

    REDIS_HOST: str
    REDIS_PORT: str

    SENDER_EMAIL: str
    EMAIL_APP_KEY: str
    SMTP_PORT: int
    SMTP_SERVER: str

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int
    JWT_SECRET_ACCESS_KEY: str
    JWT_SECRET_REFRESH_KEY: str
    JWT_ALGORITHM: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
