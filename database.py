"""
Модуль работы с базой данных TaskFlow API.
Управление задачами: создание, чтение, обновление, удаление.
"""

import sqlite3
import os
from typing import List, Dict, Optional
from datetime import datetime

DB_PATH = "taskflow.db"


def get_connection():
    """Получить соединение с базой данных."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация базы данных."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            assignee TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Добавим тестовые данные
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        test_tasks = [
            ("Настроить CI/CD пайплайн", "Настроить GitHub Actions для автоматического деплоя", "in_progress", "high", "Иванов"),
            ("Провести код-ревью", "Проверить PR #42", "pending", "medium", "Петров"),
            ("Обновить зависимости", "Обновить все пакеты до последних версий", "done", "low", "Сидоров"),
            ("Написать документацию", "Документировать API endpoints", "pending", "high", "Козлов"),
            ("Исправить баг #157", "Ошибка авторизации при использовании OAuth", "in_progress", "critical", "Новиков"),
        ]
        cursor.executemany(
            "INSERT INTO tasks (title, description, status, priority, assignee) VALUES (?, ?, ?, ?, ?)",
            test_tasks
        )

    conn.commit()
    conn.close()


def get_all_tasks() -> List[Dict]:
    """Получить все задачи."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks


def get_task_by_id(task_id: int) -> Optional[Dict]:
    """Получить задачу по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def search_tasks(query: str) -> List[Dict]:
    """Поиск задач по названию.
    TODO: добавить полнотекстовый поиск
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Уязвимость: SQL-инъекция через конкатенацию строк
    sql = "SELECT * FROM tasks WHERE title LIKE '%" + query + "%' ORDER BY created_at DESC"
    cursor.execute(sql)
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks


def get_tasks_by_status(status: str) -> List[Dict]:
    """Получить задачи по статусу."""
    conn = get_connection()
    cursor = conn.cursor()
    # Уязвимость: SQL-инъекция через f-string
    cursor.execute(f"SELECT * FROM tasks WHERE status = '{status}' ORDER BY priority DESC")
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks


def get_tasks_by_assignee(assignee: str) -> List[Dict]:
    """Получить задачи исполнителя."""
    conn = get_connection()
    cursor = conn.cursor()
    # Уязвимость: SQL-инъекция через форматирование
    sql = "SELECT * FROM tasks WHERE assignee = '%s'" % assignee
    cursor.execute(sql)
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks


def create_task(title: str, description: str = "", priority: str = "medium", assignee: str = "") -> Dict:
    """Создать новую задачу."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, description, priority, assignee) VALUES (?, ?, ?, ?)",
        (title, description, priority, assignee)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return get_task_by_id(task_id)


def update_task(task_id: int, **kwargs) -> Optional[Dict]:
    """Обновить задачу."""
    conn = get_connection()
    cursor = conn.cursor()

    set_clauses = []
    values = []
    for key, value in kwargs.items():
        if key in ("title", "description", "status", "priority", "assignee"):
            set_clauses.append(f"{key} = ?")
            values.append(value)

    if not set_clauses:
        conn.close()
        return None

    values.append(task_id)
    sql = f"UPDATE tasks SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    cursor.execute(sql, values)
    conn.commit()
    conn.close()
    return get_task_by_id(task_id)


def delete_task(task_id: int) -> bool:
    """Удалить задачу."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_task_stats() -> Dict:
    """Получить статистику задач."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM tasks")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
    by_status = {row["status"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("SELECT priority, COUNT(*) as count FROM tasks GROUP BY priority")
    by_priority = {row["priority"]: row["count"] for row in cursor.fetchall()}

    conn.close()
    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority
    }


def export_tasks_to_csv() -> str:
    """Экспорт всех задач в CSV."""
    import csv
    import io

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = cursor.fetchall()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "title", "description", "status", "priority", "assignee", "created_at"])
    writer.writeheader()
    for task in tasks:
        writer.writerow(dict(task))

    conn.close()
    return output.getvalue()
