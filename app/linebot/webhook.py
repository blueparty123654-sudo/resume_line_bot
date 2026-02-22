from fastapi import Request, APIRouter, HTTPException
from linebot.v3.exceptions import InvalidSignatureError
from app.linebot.handler import handler

router = APIRouter()

@router.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        raise HTTPException(status_code=400, detail="Invalid signature.")

    return "OK"