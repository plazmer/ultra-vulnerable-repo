"""
Конфигурация приложения TaskFlow API.
Содержит настройки подключения к БД, внешним сервисам и параметры безопасности.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./taskflow.db")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "SuperSecret123!")

# AWS Credentials для хранения отчётов
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
AWS_S3_BUCKET = "taskflow-reports"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Внешние API
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "sk_live_4eC39HqLyjWDarjtT1zdp7dc")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "SG.xxxxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy")

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "my-super-secret-key-for-jwt-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Admin
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Application
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
APP_VERSION = "1.0.0"
