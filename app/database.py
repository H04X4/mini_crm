from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# === ИСПОЛЬЗУЕМ IN-MEMORY SQLite ===
# Данные живут пока работает сервер
# Для тестового задания этого достаточно

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    echo=False  # Поставьте True для отладки SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Храним флаг инициализации
_db_initialized = False


def get_db():
    """Dependency для получения сессии БД"""
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Создание всех таблиц"""
    # Импортируем модели чтобы они зарегистрировались в Base.metadata
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized (in-memory SQLite)")