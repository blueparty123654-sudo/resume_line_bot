import sqlite3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# นำเข้า router ของ Line Bot ที่คุณมีอยู่แล้ว
from app.linebot.webhook import router as webhook_router

app = FastAPI()

# 1. อนุญาตให้เว็บเข้าถึงโฟลเดอร์ resumes ได้ (เอาไว้ให้ HR เปิดดู PDF)
app.mount("/resumes", StaticFiles(directory="resumes"), name="resumes")

# 2. ตั้งค่าโฟลเดอร์ที่เก็บไฟล์ HTML
templates = Jinja2Templates(directory="app/templates")

# 3. สร้างเส้นทางสำหรับหน้า Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    # ดึงข้อมูลจาก Database
    conn = sqlite3.connect('resume_bot.db')
    conn.row_factory = sqlite3.Row # ทำให้เรียกชื่อคอลัมน์ได้ง่ายๆ
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applicants ORDER BY id DESC")
    applicants = cursor.fetchall()
    conn.close()
    
    # ส่งข้อมูลไปแสดงที่ไฟล์ dashboard.html
    return templates.TemplateResponse("dashboard.html", {"request": request, "applicants": applicants})

# นำเข้า Route ของ Line Bot (อันเดิมของคุณ)
app.include_router(webhook_router)