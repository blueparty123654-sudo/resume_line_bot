from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.linebot.webhook import router as webhook_router

app = FastAPI(title="Resume AI Bot API")

# อนุญาตให้เว็บเข้าถึงโฟลเดอร์ resumes (เอาไว้ให้ Dashboard เปิดดู PDF ได้)
app.mount("/resumes", StaticFiles(directory="resumes"), name="resumes")

# รวม Route ของ Line Bot Webhook
app.include_router(webhook_router)