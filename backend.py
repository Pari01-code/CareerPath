from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.hash import bcrypt
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

app = FastAPI()

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")
templates = Jinja2Templates(directory="frontend")

DB_NAME = "database.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            percent INTEGER,
            color TEXT DEFAULT 'pink-main',
            note TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()

init_db()

# --------------------------
# Pages
# --------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/ai", response_class=HTMLResponse)
def ai_page(request: Request):
    return templates.TemplateResponse("ai.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request):
    return templates.TemplateResponse("analytics.html", {"request": request})

@app.get("/edit-profile", response_class=HTMLResponse)
def edit_profile_page(request: Request):
    return templates.TemplateResponse("edit-profile.html", {"request": request})

@app.get("/question-after-register", response_class=HTMLResponse)
def question_after_register_page(request: Request):
    return templates.TemplateResponse("question-after-register.html", {"request": request})

# --------------------------
# Auth APIs
# --------------------------
@app.post("/api/register")
def register(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    c = conn.cursor()

    password_hash = bcrypt.hash(password[:71])

    try:
        c.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()

        # after registration go to question page (matches your frontend)
        return RedirectResponse("/question-after-register", status_code=303)

    except sqlite3.IntegrityError:
        return JSONResponse({"error": "Email already exists"}, status_code=400)
    finally:
        conn.close()

@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()

    if user and bcrypt.verify(password[:71], user["password_hash"]):
        response = RedirectResponse("/dashboard", status_code=303)
        response.set_cookie(key="user_id", value=str(user["id"]), httponly=True)
        return response

    return JSONResponse({"error": "Invalid credentials"}, status_code=401)

# --------------------------
# User data APIs
# --------------------------
@app.get("/api/user-info")
def user_info(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
    user_data = c.fetchone()
    if not user_data:
        conn.close()
        return JSONResponse({"error": "User not found"}, status_code=404)

    c.execute("SELECT name, percent, color, note FROM skills WHERE user_id = ?", (user_id,))
    skills = [dict(row) for row in c.fetchall()]
    conn.close()

    return {
        "name": user_data["name"],
        "membership": "Pro Member",
        "profilePic": "https://i.pravatar.cc/150?img=65",
        "readiness": 82,
        "sessionsCompleted": 14,
        "improvementRate": "+18%",
        "skills": skills
    }

@app.post("/api/add-skill")
def add_skill(user_id: int = Form(...), name: str = Form(...), percent: int = Form(...)):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO skills (user_id, name, percent, color, note) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, percent, "pink-main", "Newly added skill")
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/analytics-data")
def analytics_data():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) AS total FROM users")
    total_users = c.fetchone()["total"]

    c.execute("SELECT COUNT(*) AS total FROM ai_queries")
    total_queries = c.fetchone()["total"]

    # queries today
    c.execute("SELECT COUNT(*) AS total FROM ai_queries WHERE date(timestamp) = date('now')")
    queries_today = c.fetchone()["total"]

    conn.close()
    return {
        "total_users": total_users,
        "queries_today": queries_today,
        "total_queries": total_queries
    }
