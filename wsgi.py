from app import create_app
from app.shop_app import create_shop_app

app = create_app()
shop_app = create_shop_app()

from werkzeug.middleware.dispatcher import DispatcherMiddleware

application = DispatcherMiddleware(app, {'/shop': shop_app,})
