Triển khai Docker
docker compose down -v
docker compose up -d --build
cần có file:
.env.prod
docker-compose.yml
nginx.prod.conf
gunicorn.conf.py

docker exec -i erpjs_db psql -U [user_cua_ban] -d [ten_database] < data.sql
docker exec -it erpjs_db psql -U postgres -d [ten_db] -f /data.sql

# Tất cả chạy Docker (db + redis + web + nginx)

🚀 TỔNG QUAN KIẾN TRÚC

Bạn sẽ có 4 service:

    web → Flask API
    db → PostgreSQL
    redis → cache / queue
    nginx → reverse proxy
    👉 Tất cả chạy chung 1 network Docker

=====================================
🧱 BƯỚC 1: Chuẩn bị thư mục
-Tạo cấu trúc:
ERPVIET/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── app/
│ └── main.py
├── nginx/
│ └── default.conf

    ⚙️ BƯỚC 2: Viết docker-compose.yml

====================================
version: "3.9"

services:
web:
build: .
container_name: erp_web
restart: always
ports: - "8000:8000"
environment:
DATABASE_URL: postgresql://bamboo:boxi2008@db:5432/erpmini
REDIS_HOST: redis
REDIS_PORT: 6379
depends_on: - db - redis

db:
image: postgres:15
container_name: erp_db
restart: always
environment:
POSTGRES_DB: erpmini
POSTGRES_USER: bamboo
POSTGRES_PASSWORD: boxi2008
volumes: - pgdata:/var/lib/postgresql/data

redis:
image: redis:6.2-alpine
container_name: erp_redis
restart: always

nginx:
image: nginx:latest
container_name: erp_nginx
ports: - "80:80"
volumes: - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
depends_on: - web

    volumes:
    pgdata:

======================================
🐍 BƯỚC 3: Dockerfile (Flask)
FROM python:3.10

    WORKDIR /app

    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY . .

    CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app.main:app"]

    📦 BƯỚC 4: requirements.txt
    flask
    gunicorn
    psycopg2-binary
    redis

🧠 BƯỚC 5: Code Flask (rất quan trọng)
📍 app/main.py
========================================
from flask import Flask
import os
import redis
import psycopg2

app = Flask(**name**)

    # Redis
        redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        decode_responses=True
    )

    # Postgres
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))

@app.route("/")
def home():
redis_client.set("msg", "ERPVIET")
msg = redis_client.get("msg")

    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    time = cur.fetchone()

    return {
        "redis": msg,
        "db_time": str(time)
    }

============================
