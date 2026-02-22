import os
import sqlite3
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FileMessageContent, FollowEvent
from linebot.v3.messaging import (
    MessagingApi, MessagingApiBlob, ReplyMessageRequest,
    TextMessage, FlexMessage, Configuration, ApiClient,
)

from app.config import CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET
from app.database import get_waiting_resume_by_user
from app.modules.resume_service import process_resume_from_line

from .utils import flex_main_menu, flex_jobs, flex_contact, flex_application_history
from .hr_handler import flex_hr_menu, is_hr, process_hr_message

handler = WebhookHandler(CHANNEL_SECRET)
user_states = {}
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

UPLOAD_DIR = "resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# 1. Handler: จัดการข้อความ (Text)
# ─────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text
    user_id = event.source.user_id

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        reply_messages = []

        # เช็กคำสั่ง HR
        if process_hr_message(user_text, user_id, reply_messages):
            api.reply_message(ReplyMessageRequest(replyToken=event.reply_token, messages=reply_messages))
            return

        # เมนูทั่วไปของผู้ใช้
        if user_text == "ดูตำแหน่งงาน":
            reply_messages.append(FlexMessage(alt_text="รายการตำแหน่งงาน", contents=flex_jobs()))
        elif user_text == "เมนู":
            reply_messages.append(FlexMessage(alt_text="เมนูหลัก", contents=flex_main_menu()))
        elif user_text == "ดูประวัติการสมัคร":
            reply_messages.append(FlexMessage(alt_text="ประวัติการสมัครของคุณ", contents=flex_application_history(user_id)))
        elif user_text == "วิธีการใช้งาน":
            instructions = (
                "💡 วิธีการใช้งานระบบรับสมัครงาน\n\n"
                "1️⃣ กดปุ่ม 'ดูตำแหน่งงาน' เพื่อดูตำแหน่งที่เปิดรับ\n"
                "2️⃣ เลือกตำแหน่งที่สนใจ แล้วกด 'สมัครตำแหน่งนี้'\n"
                "3️⃣ ส่งไฟล์ Resume (PDF ภาษาอังกฤษ) เข้ามาในแชท\n"
                "4️⃣ ระบบ AI จะประเมินและส่งข้อมูลให้ HR ต่อไปครับ 🎉"
            )
            reply_messages.append(TextMessage(text=instructions))
        elif user_text == "ติดต่อเจ้าหน้าที่":
            reply_messages.append(FlexMessage(alt_text="ติดต่อ HR", contents=flex_contact()))

        # เมนู HR
        elif user_text == "เมนูแอดมิน":
            if is_hr(user_id):
                reply_messages.append(FlexMessage(alt_text="เมนู HR", contents=flex_hr_menu()))
            else:
                reply_messages.append(TextMessage(text="❌ ขออภัยครับ คุณไม่มีสิทธิ์เข้าถึงส่วนนี้"))

        # ระบบสมัครงาน
        elif user_text.startswith("สนใจสมัครตำแหน่ง:"):
            job_id = user_text.split(":")[-1].strip() 
    
            conn = sqlite3.connect('resume_bot.db')
            cursor = conn.cursor()
            cursor.execute("SELECT is_active FROM jobs_status WHERE job_id = ?", (job_id,))
            res = cursor.fetchone()
            conn.close()

            if res is None or res[0] == 0:
                reply_messages.append(TextMessage(text="❌ ขออภัยครับ ตำแหน่งนี้ปิดรับสมัครแล้ว"))
                if user_id in user_states: del user_states[user_id]
            else:
                user_states[user_id] = {"state": "waiting_for_resume", "apply_for": job_id}
                reply_messages.append(
                    TextMessage(text=f"✅ คุณกำลังสมัครตำแหน่ง: {job_id}\n\nกรุณาส่งไฟล์ Resume (PDF) มาได้เลยครับ 📄")
                )

        # ยืนยันข้อมูลจาก AI
        elif user_text in ["ถูกต้อง", "แก้ไข"]:
            if user_id in user_states and user_states[user_id].get("state") == "waiting_for_confirm":
                if user_text == "แก้ไข":
                    reply_messages.append(TextMessage(text="🔄 ยกเลิกข้อมูลเดิมแล้วครับ กรุณาส่งไฟล์ Resume (PDF) เข้ามาใหม่ได้เลย"))
                    user_states[user_id]["state"] = "waiting_for_resume"
                elif user_text == "ถูกต้อง":
                    db_data = get_waiting_resume_by_user(user_id)
                    if db_data:
                        score = db_data.get('score', 0)
                        summary = db_data.get('summary', 'ไม่มีสรุปข้อมูล')
                        
                        reply_msg = (
                            f"✅ ส่ง Resume เรียบร้อยแล้วครับ!\n━━━━━━━━━━━━━━━\n"
                            f"💯 คะแนนประเมิน AI: {score}/100\n"
                            f"📝 สรุป: {summary}\n━━━━━━━━━━━━━━━\n"
                            f"HR ได้รับข้อมูลของคุณแล้ว และจะติดต่อกลับในภายหลัง 🎉"
                        )
                        reply_messages.append(TextMessage(text=reply_msg))
                        
                        # อัปเดตสถานะเป็น confirmed
                        conn = sqlite3.connect('resume_bot.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE applicants SET status = 'confirmed' WHERE user_id = ? AND status = 'waiting_confirm'", (user_id,))
                        conn.commit()
                        conn.close()

                        if user_id in user_states: del user_states[user_id]
                    else:
                        reply_messages.append(TextMessage(text="❌ ไม่พบข้อมูลที่รอการยืนยัน กรุณาส่งไฟล์ใหม่ครับ"))
                        if user_id in user_states: del user_states[user_id]

        if reply_messages:
            api.reply_message(ReplyMessageRequest(replyToken=event.reply_token, messages=reply_messages))


# ─────────────────────────────────────────────
# 2. Handler: จัดการไฟล์อัปโหลด (File)
# ─────────────────────────────────────────────
@handler.add(MessageEvent, message=FileMessageContent)
def handle_file(event):
    user_id = event.source.user_id
    message_id = event.message.id

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        blob_api = MessagingApiBlob(api_client)

        if user_id not in user_states or user_states[user_id].get("state") != "waiting_for_resume":
            api.reply_message(ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="❌ กรุณากด 'สมัครตำแหน่งนี้' ในเมนู 'ดูตำแหน่งงาน' ก่อนส่งไฟล์ครับ")]
            ))
            return

        job_id = user_states[user_id]["apply_for"]
        user_states[user_id]["state"] = "processing"

        try:
            # ดาวน์โหลดไฟล์
            file_content = blob_api.get_message_content(message_id)
            file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{message_id}.pdf")
            
            with open(file_path, "wb") as f:
                f.write(file_content)

            # ส่งให้ AI ประมวลผล
            result = process_resume_from_line(user_id, file_path, job_id) 

            # ตรวจสอบความถูกต้องของข้อมูลจาก AI
            if isinstance(result, str):
                if "error" in result.lower() or "ไม่ใช่" in result:
                    user_states[user_id]["state"] = "waiting_for_resume"
                    reply_msg = TextMessage(text="❌ ระบบไม่พบข้อมูล Resume ในไฟล์นี้ กรุณาส่งไฟล์ที่ถูกต้องใหม่ครับ")
                else:
                    db_data = get_waiting_resume_by_user(user_id)
                    if db_data and db_data.get('full_name') and str(db_data.get('full_name')).strip().lower() != 'none':
                        user_states[user_id]["state"] = "waiting_for_confirm"
                        user_states[user_id]["temp_data"] = db_data
                        
                        confirm_text = (
                            "🔎 ตรวจพบข้อมูลของคุณดังนี้:\n\n"
                            f"👤 ชื่อ: {db_data.get('full_name', 'ไม่ระบุ')}\n"
                            f"📧 อีเมล: {db_data.get('email', 'ไม่ระบุ')}\n"
                            f"📞 เบอร์โทร: {db_data.get('phone', 'ไม่ระบุ')}\n\n"
                            "ข้อมูลนี้ถูกต้องหรือไม่ครับ?\n(พิมพ์ 'ถูกต้อง' หรือ 'แก้ไข')"
                        )
                        reply_msg = TextMessage(text=confirm_text)
                    else:
                        user_states[user_id]["state"] = "waiting_for_resume"
                        reply_msg = TextMessage(text="❌ อ่านข้อมูลไม่สำเร็จ ดูเหมือนจะไม่ใช่ Resume กรุณาส่งไฟล์ใหม่ครับ")

            elif isinstance(result, dict):
                if "error" in result or not result.get('full_name') or str(result.get('full_name')).strip().lower() == 'none':
                    user_states[user_id]["state"] = "waiting_for_resume"
                    reply_msg = TextMessage(text="❌ ระบบไม่พบข้อมูลส่วนตัวในไฟล์นี้ กรุณาส่งใหม่อีกครั้ง")
                else:
                    user_states[user_id]["state"] = "waiting_for_confirm"
                    user_states[user_id]["temp_data"] = result
                    
                    confirm_text = (
                        "🔎 ตรวจพบข้อมูลของคุณดังนี้:\n\n"
                        f"👤 ชื่อ: {result.get('full_name', 'ไม่ระบุ')}\n"
                        f"📧 อีเมล: {result.get('email', 'ไม่ระบุ')}\n"
                        f"📞 เบอร์โทร: {result.get('phone', 'ไม่ระบุ')}\n\n"
                        "ข้อมูลนี้ถูกต้องหรือไม่ครับ?\n(พิมพ์ 'ถูกต้อง' หรือ 'แก้ไข')"
                    )
                    reply_msg = TextMessage(text=confirm_text)
            else:
                user_states[user_id]["state"] = "waiting_for_resume"
                reply_msg = TextMessage(text="❌ AI ตอบกลับผิดพลาด กรุณาลองใหม่อีกครั้งครับ")

            api.reply_message(ReplyMessageRequest(replyToken=event.reply_token, messages=[reply_msg]))

        except Exception:
            user_states[user_id]["state"] = "waiting_for_resume"
            api.reply_message(ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="❌ เกิดข้อผิดพลาดของระบบ กรุณาส่งไฟล์ใหม่อีกครั้งครับ")]
            ))

# ─────────────────────────────────────────────
# 3. Handler: ติดตามบอท (Follow)
# ─────────────────────────────────────────────
@handler.add(FollowEvent)
def handle_follow(event):
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        welcome_msg = (
            "👋 สวัสดีครับ! ยินดีต้อนรับสู่ระบบรับสมัครงาน\n\n"
            "คุณสามารถพิมพ์ 'เมนู' หรือกดเมนูด้านล่างเพื่อดูตำแหน่งงานที่เปิดรับได้เลยครับ!"
        )
        api.reply_message(ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[
                TextMessage(text=welcome_msg),
                FlexMessage(alt_text="เมนูหลัก", contents=flex_main_menu())
            ]
        ))