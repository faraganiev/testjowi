from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")  # без eventlet/gevent
login_manager = LoginManager()
csrf = CSRFProtect()
