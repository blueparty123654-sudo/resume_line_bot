from fastapi import FastAPI
from app.linebot.webhook import router as webhook_router

app = FastAPI()

app.include_router(webhook_router)