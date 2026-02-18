from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.hash import bcrypt
from pydantic import BaseModel
from openai import OpenAI
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# --------------------------
# App & OpenAI setup
# --------------------------
app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")
templates = Jinja2Templates(directory="frontend")

# --------------------------
# DB setup (Render-friendly)
# --------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.getenv("DB_PATH", os.path.join(BASE_DIR, "database.db"))

def get_db():
    return sqlite3.connect(DB_NAME, timeout=30)

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
            color TEXT,
            note TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# --------------------------
# Page routes
# --------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/question-after-register", response_class=HTMLResponse)
def question_page(request: Request):
    return templates.TemplateResponse("question-after-register.html", {"request": request})

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

@app.get("/log-out", response_class=HTMLResponse)
def logout_page(request: Request):
    return templates.TemplateResponse("log-out.html", {"request": request})

# --------------------------
# User Management APIs
# --------------------------
@app.post("/api/register")
def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    conn = get_db()
    c = conn.cursor()

    # bcrypt safety (72 char limit)
    password_hash = bcrypt.hash(password[:71])

    try:
        c.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()
        return RedirectResponse("/question-after-register", status_code=303)

    except sqlite3.IntegrityError:
        return JSONResponse({"error": "Email already exists"}, status_code=400)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    finally:
        conn.close()

@app.post("/api/login")
def login(
    email: str = Form(...),
    password: str = Form(...)
):
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email,)
        )
        user = c.fetchone()

    except Exception as e:
        conn.close()
        return JSONResponse({"error": str(e)}, status_code=500)

    finally:
        try:
            conn.close()
        except:
            pass

    if user and bcrypt.verify(password, user[1]):
        return RedirectResponse("/dashboard", status_code=303)

    return JSONResponse({"error": "Invalid credentials"}, status_code=400)

# --------------------------
# API: User Info
# --------------------------
@app.get("/api/user-info")
def user_info(user_id: int = 1):
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute("SELECT name, email FROM users WHERE id = ?", (user_id,))
        user_data = c.fetchone()

        if not user_data:
            return JSONResponse({"error": "User not found"}, status_code=404)

        c.execute(
            "SELECT name, percent, color, note FROM skills WHERE user_id = ?",
            (user_id,)
        )

        skills = [
            {"name": row[0], "percent": row[1], "color": row[2], "note": row[3]}
            for row in c.fetchall()
        ]

        return {
            "name": user_data[0],
            "membership": "Pro Member",
            "profilePic": "https://i.pravatar.cc/150?img=65",
            "readiness": 82,
            "sessionsCompleted": 14,
            "improvementRate": "+18%",
            "skills": skills
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    finally:
        conn.close()

# --------------------------
# API: Add Skill
# --------------------------
@app.post("/api/add-skill")
def add_skill(
    user_id: int = Form(...),
    name: str = Form(...),
    percent: int = Form(...),
    note: str = Form("")
):
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute(
            "INSERT INTO skills (user_id, name, percent, color, note) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, percent, "primary", note)
        )
        conn.commit()
        return {"status": "success"}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    finally:
        conn.close()

# --------------------------
# AI API
# --------------------------
class UserInput(BaseModel):
    text: str
    user_id: int | None = None

@app.post("/api/ai-response")
def ai_response(input: UserInput):
    try:
        # If key missing, fail gracefully
        if not os.getenv("OPENAI_API_KEY"):
            return JSONResponse({"error": "OPENAI_API_KEY not set"}, status_code=500)

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": input.text}]
        )

        response_text = completion.choices[0].message.content

        if input.user_id:
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(
                    "INSERT INTO ai_queries (user_id, query, response) VALUES (?, ?, ?)",
                    (input.user_id, input.text, response_text)
                )
                conn.commit()
            finally:
                conn.close()

        return {"response": response_text}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --------------------------
# Analytics API
# --------------------------
@app.get("/api/analytics-data")
def analytics_data():
    conn = get_db()
    c = conn.cursor()

    try:
        c.execute("SELECT COUNT(*) FROM users")
        users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM ai_queries WHERE DATE(timestamp) = DATE('now')")
        today_queries = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM ai_queries")
        total_queries = c.fetchone()[0]

        return {
            "total_users": users,
            "queries_today": today_queries,
            "total_queries": total_queries
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    finally:
        conn.close()
