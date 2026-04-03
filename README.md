# TaskFlow API — Сервис управления задачами

Простой REST API для управления задачами команды.

## Возможности

- CRUD задач
- Фильтрация по статусу и приоритету
- Поиск по названию
- Экспорт отчётов

## Быстрый старт

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Docker

```bash
docker-compose up --build
```

API доступен на `http://localhost:8000`
