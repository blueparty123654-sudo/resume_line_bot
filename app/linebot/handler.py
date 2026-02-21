from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    Configuration,
    ApiClient,
)

from app.config import CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET
from .hand import flex_menu


handler = WebhookHandler(CHANNEL_SECRET)

configuration = Configuration(
    access_token=CHANNEL_ACCESS_TOKEN
)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    user_text = event.message.text

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)

        # เมนู
        if user_text == "เมนู":
            api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[
                        FlexMessage(
                            alt_text="เมนู",
                            contents=flex_menu()
                        )
                    ],
                )
            )

        else:
            api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[
                        TextMessage(
                            text=f"FastAPI ได้รับข้อความ: {user_text}"
                        )
                    ],
                )
            )