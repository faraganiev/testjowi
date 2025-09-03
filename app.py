import os
import logging
from logging import StreamHandler
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFError
from werkzeug.security import generate_password_hash
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import text

from extensions import db, socketio, login_manager, csrf
from models import Product, User
from routes.orders import orders_bp
from routes.auth import auth_bp

load_dotenv()

def create_app():
    app = Flask(__name__)

    # --- CONFIG ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///database.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"

    # --- INIT EXTENSIONS ---
    db.init_app(app)
    csrf.init_app(app)

    # Socket.IO: используем Redis ТОЛЬКО если он реально доступен
    redis_url = os.getenv("REDIS_URL")
    use_mq = False
    if redis_url:
        try:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            use_mq = True
            app.logger.info("Socket.IO: using Redis message queue at %s", redis_url)
        except Exception as e:
            app.logger.warning("Socket.IO: Redis is not reachable (%s). Falling back to local mode.", e)

    if use_mq:
        socketio.init_app(app, message_queue=redis_url)
    else:
        socketio.init_app(app)  # локальный режим, без очереди

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        # фикс предупреждения SQLAlchemy 2.0: используем session.get
        return db.session.get(User, int(user_id))

    # Prometheus /metrics
    metrics = PrometheusMetrics(app)
    metrics.info("app_info", "Order system", version="1.0.0")

    # --- BLUEPRINTS ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)

    # --- LOGGING (stdout) ---
    handler = StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    @app.before_request
    def _log_request():
        app.logger.info("request path=%s method=%s ip=%s", request.path, request.method, request.remote_addr)

    # --- ERROR PAGES ---
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error")
        return render_template("errors/500.html"), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning("CSRF error: %s path=%s ip=%s", e.description, request.path, request.remote_addr)
        return render_template("errors/csrf.html", reason=e.description), 400

    # --- HEALTHCHECK ---
    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}, 200
        except Exception as ex:
            app.logger.exception("healthz")
            return {"status": "error", "message": str(ex)}, 500

    # --- DB SEED ---
    with app.app_context():
        db.create_all()
        if not Product.query.first():
            db.session.add_all([
                Product(name="Пицца Маргарита", price=55000, category="Еда"),
                Product(name="Бургер Классический", price=32000, category="Еда"),
                Product(name="Картофель фри", price=15000, category="Еда"),
                Product(name="Кола 0.5", price=11000, category="Напитки"),
                Product(name="Спрайт 0.5", price=11000, category="Напитки"),
            ])
        if not User.query.filter_by(username="admin").first():
            db.session.add(User(username="admin", password_hash=generate_password_hash("admin")))
        db.session.commit()

    return app

app = create_app()

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_ENV") != "production",
        allow_unsafe_werkzeug=True
    )
