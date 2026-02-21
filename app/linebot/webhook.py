from fastapi import Request, APIRouter, HTTPException
from linebot.v3.exceptions import InvalidSignatureError # เพิ่มตัวดักจับ Error
from app.linebot.handler import handler

router = APIRouter()

@router.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    # ใช้ .get() เพื่อป้องกัน Error ถ้า Header ไม่มี X-Line-Signature ส่งมา
    signature = request.headers.get("X-Line-Signature", "")

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        # คืนค่า 400 ถ้า Signature ไม่ตรง
        raise HTTPException(status_code=400, detail="Invalid signature.")

    return "OK"