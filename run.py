import os
from app import create_app
from app.shop_app import create_shop_app

app = create_app()
shop_app = create_shop_app()

# Gộp cả 2 app vào 1 WSGI middleware để cùng phục vụ trên port 5000
# ERP: /... 
# Shop: /shop/...
from werkzeug.middleware.dispatcher import DispatcherMiddleware

application = DispatcherMiddleware(app, {'/shop': shop_app,})


mode = os.getenv("FLASK_ENV", os.getenv("APP_MODE", "dev")).lower()

from waitress import serve


def run_dev():
    print("DEV MODE")
    # Serve WSGI dispatcher so /shop/* works
    serve(
        application,
        host="0.0.0.0",
        port=5000,
        threads=4,
    )



def run_prod():
    print("PROD MODE (Waitress)")
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    logging.getLogger("waitress").setLevel(logging.INFO)
    serve(
        application,
        host="0.0.0.0",   # không expose trực tiếp internet
        port=5000,
        threads=int(os.getenv("THREADS", 4)),
        connection_limit=100,
        cleanup_interval=30,
        channel_timeout=30
    )


if __name__ == "__main__":
    if mode == "dev":
        run_dev()
    else:
        run_prod()