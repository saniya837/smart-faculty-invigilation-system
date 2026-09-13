import os
from urllib.parse import quote_plus


class Config:

    SECRET_KEY = "smart-faculty-local-secret-key"

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Local MySQL configuration
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "Sanu@123"
    MYSQL_HOST = "127.0.0.1"
    MYSQL_PORT = "3306"
    MYSQL_DB = "smart_invigilation_db"

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://"
        f"{MYSQL_USER}:{quote_plus(MYSQL_PASSWORD)}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        f"?charset=utf8mb4"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "echo": False
    }

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    REPORTS_FOLDER = os.path.join(BASE_DIR, "reports")

    RULE_PRIORITIZE_BALANCE = True