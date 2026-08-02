import time
import psycopg2
import os

DB_HOST = os.getenv("DB_HOST") or os.getenv("PGHOST", "localhost")
DB_NAME = os.getenv("DB_NAME") or os.getenv("PGDATABASE")
DB_USER = os.getenv("DB_USER") or os.getenv("PGUSER")
DB_PASS = os.getenv("DB_PASS") or os.getenv("PGPASSWORD") or ""

if not DB_NAME or not DB_USER:
    if os.getenv("DATABASE_URL"):
        try:
            from urllib.parse import urlparse
            p = urlparse(os.getenv("DATABASE_URL"))
            if p.hostname:
                DB_HOST = p.hostname
            if p.path and p.path != "/":
                DB_NAME = p.path.lstrip("/")
            if p.username:
                DB_USER = p.username
            if p.password:
                DB_PASS = p.password
        except Exception:
            pass

if not DB_NAME or not DB_USER or not DB_PASS:
    print("❌ Missing DB credentials. Set DB_NAME, DB_USER, DB_PASS environment variables.")
    exit(1)

for i in range(10):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        conn.close()
        print("✅ DB READY")
        break
    except Exception:
        print("⏳ Waiting for DB...")
        time.sleep(2)
else:
    print("❌ DB NOT READY")
    exit(1)

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    conn.autocommit = True
    cur = conn.cursor()

    print("🔧 Checking online_orders.tracking_token column...")
    cur.execute("""
        ALTER TABLE online_orders
        ADD COLUMN IF NOT EXISTS tracking_token VARCHAR(64) NULL
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_online_orders_tracking_token
        ON online_orders (tracking_token)
    """)
    cur.close()
    conn.close()
    print("✅ Direct SQL migration applied")
except Exception as sql_err:
    print(f"❌ Direct SQL migration failed: {sql_err}")
    exit(1)

try:
    import subprocess
    result = subprocess.run(
        ["python", "-m", "flask", "db", "upgrade"],
        env={**os.environ, "FLASK_APP": "wsgi.py"},
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"⚠️ flask db upgrade failed: {result.stderr}")
    else:
        print("✅ FLASK MIGRATIONS APPLIED")
except Exception as e:
    print(f"⚠️ flask db upgrade error: {e}")
