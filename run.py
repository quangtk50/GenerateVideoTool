"""Khởi động web: python run.py  ->  mở http://127.0.0.1:8000 (đổi bằng HOST/PORT trong .env)"""
import uvicorn

from app import config

if __name__ == "__main__":
    uvicorn.run("app.web:app", host=config.HOST, port=config.PORT, reload=False)
