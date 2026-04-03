"""
Базовые тесты TaskFlow API.
Проверка основных endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from database import init_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Инициализация БД перед тестами."""
    init_db()


@pytest.fixture
def client():
    """Тестовый клиент."""
    return TestClient(app)


class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestTasksCRUD:
    def test_list_tasks(self, client):
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
        assert len(tasks) > 0

    def test_get_task_by_id(self, client):
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data

    def test_get_task_not_found(self, client):
        response = client.get("/api/tasks/99999")
        assert response.status_code == 404

    def test_create_task(self, client):
        response = client.post(
            "/api/tasks",
            json={
                "title": "Тестовая задача",
                "description": "Создана автотестом",
                "priority": "high",
                "assignee": "Тестировщик"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Тестовая задача"

    def test_update_task(self, client):
        response = client.put(
            "/api/tasks/1",
            json={"status": "done"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"

    def test_delete_task(self, client):
        # Сначала создаём задачу
        create_resp = client.post(
            "/api/tasks",
            json={"title": "Задача для удаления"}
        )
        task_id = create_resp.json()["id"]

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200


class TestSearch:
    def test_search_tasks(self, client):
        response = client.get("/api/tasks/search", params={"q": "CI/CD"})
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) > 0

    def test_search_no_results(self, client):
        response = client.get("/api/tasks/search", params={"q": "несуществующаязадачаXYZ"})
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 0


class TestStats:
    def test_get_stats(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_status" in data
        assert "by_priority" in data
