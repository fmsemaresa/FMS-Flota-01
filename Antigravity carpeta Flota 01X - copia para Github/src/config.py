import os

# Directorio raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuración de base de datos dinámica para local (SQLite) y nube (PostgreSQL)
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # Render y Heroku usan "postgres://", pero SQLAlchemy requiere "postgresql://"
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_PATH = os.path.join(BASE_DIR, "database.db")
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Carpeta de exportaciones Excel
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DOCS_DIR = os.path.join(ASSETS_DIR, "docs")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

# Notificaciones simuladas (ruta del log de notificaciones)
NOTIFICATIONS_LOG = os.path.join(BASE_DIR, "notifications_log.txt")
