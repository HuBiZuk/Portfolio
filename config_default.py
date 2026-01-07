import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'my-secret-key-1234'

    # DB 설정
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = 'MY_PASSWORD'
    DB_NAME = 'my_hotdeal'
    DB_CHARSET = 'utf8mb4'