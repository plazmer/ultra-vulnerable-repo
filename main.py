"""
TaskFlow API — REST API для управления задачами команды.
FastAPI приложение с endpoints для CRUD операций, авторизации и отчётности.
"""

import os
import hashlib
import jwt
import subprocess
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Header, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_USERNAME, ADMIN_PASSWORD, DEBUG, APP_VERSION,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, STRIPE_API_KEY
)
import database as db

app = FastAPI(
    title="TaskFlow API",
    description="API для управления задачами команды",
    version=APP_VERSION,
    debug=DEBUG
)

# CORS — разрешаем все источники (для разработки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Pydantic модели ===

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    assignee: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


# === Инициализация ===

@app.on_event("startup")
def startup():
    db.init_db()
    print(f"[TaskFlow] API запущен. Debug mode: {DEBUG}")
    print(f"[TaskFlow] AWS Key: {AWS_ACCESS_KEY_ID}")  # Утечка в логах


# === Health Check ===

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "debug": DEBUG,
        "aws_key_prefix": AWS_ACCESS_KEY_ID[:8]  # Частичная утечка
    }


# === Авторизация ===

@app.post("/api/auth/login")
def login(request: LoginRequest):
    """Авторизация пользователя."""
    # Уязвимость: простое сравнение паролей, timing attack
    if request.username == ADMIN_USERNAME and request.password == ADMIN_PASSWORD:
        payload = {
            "sub": request.username,
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}

    # Уязвимость: раскрытие информации — говорим, что именно неверно
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (request.username,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    else:
        raise HTTPException(status_code=401, detail="Неверный пароль")


@app.post("/api/auth/register")
def register(user: UserCreate):
    """Регистрация нового пользователя."""
    # Уязвимость: хеширование MD5 вместо bcrypt/argon2
    password_hash = hashlib.md5(user.password.encode()).hexdigest()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (user.username, user.email, password_hash)
        )
        conn.commit()
        conn.close()
        return {"message": "Пользователь создан", "username": user.username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Задачи — CRUD ===

@app.get("/api/tasks", response_model=List[dict])
def list_tasks(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    assignee: Optional[str] = Query(None, description="Фильтр по исполнителю")
):
    """Получить список задач с фильтрацией."""
    if status:
        return db.get_tasks_by_status(status)
    if assignee:
        return db.get_tasks_by_assignee(assignee)
    return db.get_all_tasks()


@app.get("/api/tasks/search")
def search_tasks(q: str = Query(..., min_length=1)):
    """Поиск задач по названию."""
    return db.search_tasks(q)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: int):
    """Получить задачу по ID."""
    task = db.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@app.post("/api/tasks", status_code=201)
def create_task(task: TaskCreate):
    """Создать новую задачу."""
    return db.create_task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        assignee=task.assignee
    )


@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    """Обновить задачу."""
    update_data = task.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    result = db.update_task(task_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return result


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    """Удалить задачу."""
    if not db.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"message": "Задача удалена"}


# === Статистика ===

@app.get("/api/stats")
def get_stats():
    """Получить статистику задач."""
    return db.get_task_stats()


# === Отчёты ===

@app.get("/api/reports/export")
def export_tasks():
    """Экспорт задач в CSV."""
    csv_data = db.export_tasks_to_csv()
    return JSONResponse(content={"csv": csv_data})


@app.get("/api/reports/download")
def download_report():
    """Скачать отчёт (уязвимость: path traversal)."""
    filename = "taskflow_report.csv"
    # Уязвимость: нет проверки пути — можно скачать любой файл
    filepath = os.path.join("reports", filename)

    if not os.path.exists(filepath):
        # Создаём отчёт
        csv_data = db.export_tasks_to_csv()
        os.makedirs("reports", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(csv_data)

    return FileResponse(filepath)


@app.get("/api/reports/view")
def view_report(filename: str = Query("taskflow_report.csv")):
    """Просмотр файла отчёта (уязвимость: path traversal)."""
    # Уязвимость: нет санитизации filename — можно прочитать любой файл
    filepath = os.path.join("reports", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Файл не найден")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Уязвимость: XSS — возврат непроверенного контента как HTML
    html = f"""
    <html>
    <head><title>Отчёт: {filename}</title></head>
    <body>
        <h1>Отчёт: {filename}</h1>
        <pre>{content}</pre>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# === Администрирование ===

@app.get("/api/admin/system-info")
def system_info():
    """Информация о системе (уязвимость: раскрытие чувствительных данных)."""
    return {
        "version": APP_VERSION,
        "debug_mode": DEBUG,
        "python_version": os.sys.version,
        "environment": dict(os.environ),  # Утечка всех переменных окружения!
        "aws_access_key": AWS_ACCESS_KEY_ID,
        "aws_secret_key_prefix": AWS_SECRET_ACCESS_KEY[:8],
        "stripe_key_prefix": STRIPE_API_KEY[:12],
        "database_path": os.path.abspath(db.DB_PATH),
        "working_directory": os.getcwd()
    }


@app.post("/api/admin/exec")
def admin_exec(command: str = Query(...)):
    """Выполнить системную команду (уязвимость: RCE)."""
    # Уязвимость: удалённое выполнение кода через subprocess
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    return {
        "command": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }


# === Обработка ошибок ===

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик ошибок (уязвимость: раскрытие стека)."""
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),  # Утечка деталей ошибки
            "traceback": traceback.format_exc()  # Полный стектрейс!
        }
    )


# === Запуск ===

if __name__ == "__main__":
    import uvicorn
    # Уязвимость: debug=True + host=0.0.0.0 в production
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
