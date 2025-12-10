import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


# Создаём тестовую БД в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Создаём таблицы перед каждым тестом и очищаем после"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


class TestOperators:
    def test_create_operator(self):
        response = client.post("/operators", json={
            "name": "Иван Иванов",
            "is_active": True,
            "max_active_contacts": 5
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Иван Иванов"
        assert data["is_active"] is True
        assert data["max_active_contacts"] == 5
        assert data["current_load"] == 0

    def test_list_operators(self):
        # Создаём операторов
        client.post("/operators", json={"name": "Оператор 1"})
        client.post("/operators", json={"name": "Оператор 2"})
        
        response = client.get("/operators")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_update_operator(self):
        # Создаём оператора
        create_resp = client.post("/operators", json={"name": "Test"})
        operator_id = create_resp.json()["id"]
        
        # Обновляем
        response = client.patch(f"/operators/{operator_id}", json={
            "is_active": False,
            "max_active_contacts": 20
        })
        assert response.status_code == 200
        assert response.json()["is_active"] is False
        assert response.json()["max_active_contacts"] == 20


class TestSources:
    def test_create_source(self):
        response = client.post("/sources", json={
            "name": "Telegram Bot",
            "code": "tg_bot_1",
            "description": "Основной телеграм бот"
        })
        assert response.status_code == 200
        assert response.json()["code"] == "tg_bot_1"

    def test_duplicate_code(self):
        client.post("/sources", json={"name": "Bot 1", "code": "bot1"})
        response = client.post("/sources", json={"name": "Bot 2", "code": "bot1"})
        assert response.status_code == 400


class TestAssignments:
    def test_assign_operator_to_source(self):
        # Создаём оператора и источник
        op_resp = client.post("/operators", json={"name": "Оператор"})
        src_resp = client.post("/sources", json={"name": "Бот", "code": "bot"})
        
        operator_id = op_resp.json()["id"]
        source_id = src_resp.json()["id"]
        
        # Назначаем
        response = client.post("/assignments", json={
            "operator_id": operator_id,
            "source_id": source_id,
            "weight": 10
        })
        assert response.status_code == 200
        assert response.json()["weight"] == 10


class TestContacts:
    def setup_method(self):
        """Подготовка данных для тестов обращений"""
        # Создаём операторов
        self.op1 = client.post("/operators", json={
            "name": "Оператор 1",
            "max_active_contacts": 2
        }).json()
        self.op2 = client.post("/operators", json={
            "name": "Оператор 2",
            "max_active_contacts": 2
        }).json()
        
        # Создаём источник
        self.source = client.post("/sources", json={
            "name": "Telegram",
            "code": "telegram"
        }).json()
        
        # Назначаем операторов на источник
        client.post("/assignments", json={
            "operator_id": self.op1["id"],
            "source_id": self.source["id"],
            "weight": 10
        })
        client.post("/assignments", json={
            "operator_id": self.op2["id"],
            "source_id": self.source["id"],
            "weight": 30
        })

    def test_create_contact(self):
        response = client.post("/contacts", json={
            "lead_external_id": "user_123",
            "source_code": "telegram",
            "message": "Привет!"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["lead"]["external_id"] == "user_123"
        assert data["operator_id"] is not None
        assert "distribution_info" in data

    def test_lead_reuse(self):
        """Проверяем что для одного external_id используется один лид"""
        # Первое обращение
        resp1 = client.post("/contacts", json={
            "lead_external_id": "user_456",
            "source_code": "telegram"
        })
        lead_id_1 = resp1.json()["lead_id"]
        
        # Второе обращение того же пользователя
        resp2 = client.post("/contacts", json={
            "lead_external_id": "user_456",
            "source_code": "telegram"
        })
        lead_id_2 = resp2.json()["lead_id"]
        
        assert lead_id_1 == lead_id_2

    def test_operator_limit(self):
        """Проверяем что оператор не получает обращения сверх лимита"""
        # Оператор 1 имеет лимит 2
        # Создаём 3 обращения
        operator_ids = []
        for i in range(3):
            resp = client.post("/contacts", json={
                "lead_external_id": f"user_{i}",
                "source_code": "telegram"
            })
            if resp.json()["operator_id"]:
                operator_ids.append(resp.json()["operator_id"])
        
        # У каждого оператора не должно быть больше 2 обращений
        from collections import Counter
        counts = Counter(operator_ids)
        for op_id, count in counts.items():
            assert count <= 2

    def test_close_contact(self):
        """Проверяем закрытие обращения"""
        # Создаём обращение
        resp = client.post("/contacts", json={
            "lead_external_id": "user_close",
            "source_code": "telegram"
        })
        contact_id = resp.json()["id"]
        
        # Закрываем
        close_resp = client.patch(f"/contacts/{contact_id}/status", json={
            "status": "closed"
        })
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"
        assert close_resp.json()["closed_at"] is not None

    def test_no_available_operators(self):
        """Проверяем создание обращения когда нет доступных операторов"""
        # Заполняем лимиты обоих операторов (по 2 у каждого = 4 обращения)
        for i in range(4):
            client.post("/contacts", json={
                "lead_external_id": f"fill_{i}",
                "source_code": "telegram"
            })
        
        # Пятое обращение должно создаться без оператора
        resp = client.post("/contacts", json={
            "lead_external_id": "user_no_op",
            "source_code": "telegram"
        })
        assert resp.status_code == 200
        assert resp.json()["operator_id"] is None


class TestStats:
    def test_system_stats(self):
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_operators" in data
        assert "total_sources" in data
        assert "total_leads" in data


class TestLeads:
    def test_lead_with_multiple_sources(self):
        """Проверяем что лид может иметь обращения из разных источников"""

        client.post("/sources", json={"name": "Telegram", "code": "tg"})
        client.post("/sources", json={"name": "WhatsApp", "code": "wa"})
        
        # Создаём оператора и назначаем на оба источника
        op = client.post("/operators", json={"name": "Оператор"}).json()
        src_tg = client.get("/sources").json()[0]["id"]
        src_wa = client.get("/sources").json()[1]["id"]
        
        client.post("/assignments", json={
            "operator_id": op["id"], "source_id": src_tg, "weight": 1
        })
        client.post("/assignments", json={
            "operator_id": op["id"], "source_id": src_wa, "weight": 1
        })
        
        # Создаём обращения от одного лида из разных источников
        resp1 = client.post("/contacts", json={
            "lead_external_id": "multi_source_user",
            "source_code": "tg"
        })
        resp2 = client.post("/contacts", json={
            "lead_external_id": "multi_source_user",
            "source_code": "wa"
        })
        
        # Проверяем что это один лид
        lead_id = resp1.json()["lead_id"]
        assert resp2.json()["lead_id"] == lead_id
        
        # Проверяем что у лида два обращения
        lead_resp = client.get(f"/leads/{lead_id}")
        assert len(lead_resp.json()["contacts"]) == 2