from app.database import get_waiting_resume_by_user
import sqlite3
import os

from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FileMessageContent, FollowEvent
from linebot.v3.messaging import (
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    Configuration,
    ApiClient,
)

from app.config import CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET
from app.modules.resume_service import process_resume_from_line
from .hand import flex_main_menu, flex_jobs, flex_contact
from .hand_hr import flex_hr_menu

def is_hr(user_id):
    conn = sqlite3.connect('resume_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE line_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    # ถ้ามีข้อมูลและ role เป็น 'hr' จะส่งค่า True กลับไป
    if result and result[0] == 'hr':
        return True
    return False

handler = WebhookHandler(CHANNEL_SECRET)

user_states = {}

configuration = Configuration(
    access_token=CHANNEL_ACCESS_TOKEN
)

UPLOAD_DIR = "resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# Handler: ข้อความ (Text)
# ─────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text
    user_id = event.source.user_id

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        reply_messages = []

        # ── ดูตำแหน่งงาน ─────────────────────────
        if user_text == "ดูตำแหน่งงาน":
            reply_messages.append(
                FlexMessage(
                    alt_text="รายการตำแหน่งงานที่เปิดรับ",
                    contents=flex_jobs()
                )
            )
        
        # ── สมัครงาน (รับข้อความจากปุ่มใน Flex Message) ─────────────────────────
        elif user_text.startswith("สนใจสมัครตำแหน่ง:"):
            # 1. ตัดคำว่า "สนใจสมัครตำแหน่ง: " ออก เพื่อเอาแค่ชื่อตำแหน่ง
            job_title = user_text.replace("สนใจสมัครตำแหน่ง: ", "").strip()
            
            # 2. จำสถานะว่า User คนนี้กำลังจะส่ง Resume สมัครตำแหน่งนี้
            user_states[user_id] = {
                "state": "waiting_for_resume",
                "apply_for": job_title
            }
            
            # 3. ตอบกลับให้ผู้ใช้ส่งไฟล์ PDF
            reply_messages.append(
                TextMessage(
                    text=f"คุณกำลังสมัครตำแหน่ง: {job_title}\n\nกรุณาส่งไฟล์ Resume ของคุณ (ต้องเป็นไฟล์ PDF ภาษาอังกฤษเท่านั้น) มาในแชทนี้ได้เลยครับ 📄"
                )
            )

        # ── ขั้นตอนยืนยันข้อมูลจาก AI ─────────────────────────
        elif user_text in ["ถูกต้อง", "แก้ไข"]:
            if user_id in user_states and user_states[user_id].get("state") == "waiting_for_confirm":
                
                if user_text == "แก้ไข":
                    reply_messages.append(TextMessage(text="🔄 ยกเลิกข้อมูลเดิมแล้วครับ กรุณาส่งไฟล์ Resume (PDF) เข้ามาใหม่อีกครั้งได้เลยครับ"))
                    user_states[user_id]["state"] = "waiting_for_resume" # ถอยกลับไปรอรับไฟล์ใหม่
                
                elif user_text == "ถูกต้อง":
                    # ดึงผลคะแนนที่ AI แอบประเมินและเซฟไว้แล้วจาก Database มาแสดงให้ผู้ใช้ดู
                    db_data = get_waiting_resume_by_user(user_id)
                    
                    if db_data:
                        # อัปเดตสถานะใน Database ให้เป็น confirmed
                        conn = sqlite3.connect('resume_bot.db')
                        conn.execute("UPDATE applicants SET status = 'confirmed' WHERE user_id = ? AND status = 'waiting_confirm'", (user_id,))
                        conn.commit()
                        conn.close()

                        # ส่งผลลัพธ์ให้ผู้ใช้
                        status_icon = "✅ ผ่านเกณฑ์" if db_data['passed'] else "⚠️ ไม่ผ่านเกณฑ์"
                        summary_msg = (
                            f"🎉 บันทึกข้อมูลการสมัครสำเร็จ!\n\n"
                            f"ตำแหน่ง: {db_data['job_title']}\n"
                            f"สถานะ: {status_icon}\n"
                            f"คะแนนประเมิน: {db_data['score']}/100\n\n"
                            f"🤖 สรุปจาก AI:\n{db_data['summary']}\n\n"
                            f"ข้อมูลของคุณถูกส่งให้ HR เรียบร้อยแล้วครับ ขอบคุณที่ร่วมงานกับเรา!"
                        )
                        reply_messages.append(TextMessage(text=summary_msg))
                        del user_states[user_id] # ปิดจ๊อบ ลบความจำทิ้ง
                    else:
                        reply_messages.append(TextMessage(text="❌ ไม่พบข้อมูลที่รอการยืนยัน กรุณาส่งไฟล์ใหม่ครับ"))
                        del user_states[user_id]
        
        # ── วิธีการใช้งาน ─────────────────────────
        elif user_text == "วิธีการใช้งาน":
            instructions = (
                "💡 วิธีการใช้งานระบบรับสมัครงาน\n\n"
                "1️⃣ กดปุ่ม 'ดูตำแหน่งงาน' เพื่อดูตำแหน่งที่บริษัทเปิดรับ\n"
                "2️⃣ เลือกตำแหน่งที่สนใจ แล้วกด 'สมัครตำแหน่งนี้'\n"
                "3️⃣ ส่งไฟล์ Resume (ต้องเป็นไฟล์ .pdf ภาษาอังกฤษเท่านั้น) เข้ามาในแชท\n"
                "4️⃣ ระบบ AI จะทำการประเมินเบื้องต้น และส่งข้อมูลให้ HR พิจารณาต่อไปครับ 🎉"
            )
            reply_messages.append(TextMessage(text=instructions))

        elif user_text == "ติดต่อเจ้าหน้าที่":
            reply_messages.append(
                FlexMessage(
                    alt_text="ติดต่อฝ่าย HR",
                    contents=flex_contact()
        )
    )

            

        # ── เรียกดูเมนูหลัก ─────────────────────────
        elif user_text == "เมนู":
            reply_messages.append(
                FlexMessage(
                    alt_text="เมนูหลัก",
                    contents=flex_main_menu()
                )
            )
        
        # ── (เฉพาะตอนตั้งระบบ) ลงทะเบียนตัวเองเป็น HR ─────────────────
        # elif user_text == "#ตั้งฉันเป็นแอดมิน":
            # conn = sqlite3.connect('resume_bot.db')
            # cursor = conn.cursor()
            # ใส่ข้อมูล LINE ID ของคุณลงไปในฐานะ 'hr'
            # cursor.execute("INSERT OR REPLACE INTO users (line_id, role) VALUES (?, ?)", (user_id, 'hr'))
            # conn.commit()
            # conn.close()
            # reply_messages.append(
                # TextMessage(text="✅ บันทึกสิทธิ์ HR ให้คุณเรียบร้อยแล้ว!\n\nพิมพ์ 'เมนูแอดมิน' เพื่อเริ่มใช้งานได้เลยครับ")
            # )

        # ── เรียกเมนูจัดการของ HR ─────────────────────────────────
        elif user_text == "เมนูแอดมิน":
            if is_hr(user_id): # เช็คสิทธิ์ก่อน ถ้าเป็น True ค่อยให้เห็น
                reply_messages.append(
                    FlexMessage(
                        alt_text="เมนูสำหรับจัดการ (HR)",
                        contents=flex_hr_menu()
                    )
                )
            else: # ถ้าคนนอกพิมพ์มา จะด่ากลับไป
                reply_messages.append(
                    TextMessage(text="❌ ขออภัยครับ คุณไม่มีสิทธิ์เข้าถึงส่วนนี้")
                )

        # ── สร้างงาน (HR) ─────────────────────────
        elif user_text == "#สร้างงาน":
            if is_hr(user_id):
                user_states[user_id] = {"state": "waiting_for_title"}
                reply_messages.append(
                    TextMessage(text="[โหมด HR] เริ่มการสร้างประกาศงานใหม่!\n\nกรุณาพิมพ์ 'ชื่อตำแหน่ง' ที่ต้องการรับสมัครครับ")
                )
            else:
                reply_messages.append(
                    TextMessage(text="❌ ขออภัยครับ คุณไม่มีสิทธิ์เข้าถึงส่วนนี้")
                )

        elif user_id in user_states and user_states[user_id]["state"] == "waiting_for_title":
            user_states[user_id]["title"] = user_text
            user_states[user_id]["state"] = "waiting_for_skills"
            reply_messages.append(
                TextMessage(text=f"รับทราบครับ ตำแหน่ง: {user_text}\n\nต่อไปกรุณาพิมพ์ 'ทักษะ (Skills)' ที่ต้องการ (เช่น Python, SQL, ภาษาอังกฤษ)")
            )

        elif user_id in user_states and user_states[user_id]["state"] == "waiting_for_skills":
            title = user_states[user_id]["title"]
            skills = user_text

            conn = sqlite3.connect('resume_bot.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO jobs (title, requirements) VALUES (?, ?)", (title, skills))
            conn.commit()
            conn.close()

            del user_states[user_id]
            reply_messages.append(
                TextMessage(text=f"✅ บันทึกประกาศงานลง Database สำเร็จ!\n\nตำแหน่ง: {title}\nทักษะ: {skills}")
            )
        

        # ── ดูตำแหน่งงานทั้งหมด (HR) ─────────────────────────
        elif user_text == "#ดูงานแอดมิน":
            if is_hr(user_id):
                conn = sqlite3.connect('resume_bot.db')
                cursor = conn.cursor()
                # ดึงข้อมูลทั้งหมดมาดู เพื่อให้รู้ job_id
                cursor.execute("SELECT job_id, title, status FROM jobs")
                jobs = cursor.fetchall()
                conn.close()

                if not jobs:
                    reply_messages.append(TextMessage(text="📭 ยังไม่มีข้อมูลตำแหน่งงานในระบบครับ"))
                else:
                    text_list = "📋 รายการตำแหน่งงานทั้งหมด:\n\n"
                    for j in jobs:
                        # j[0] = job_id, j[1] = title, j[2] = status
                        status_emoji = "🟢" if j[2] == 'open' else "🔴"
                        text_list += f"ID: {j[0]} | {j[1]} {status_emoji}\n"
                    
                    text_list += "\n(หากต้องการลบลำแหน่งไหน ให้พิมพ์ '#ลบงาน')"
                    reply_messages.append(TextMessage(text=text_list))
            else:
                reply_messages.append(TextMessage(text="❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้"))

        # ── ลบตำแหน่งงาน (HR) - ขั้นที่ 1 รับคำสั่ง ─────────────────
        elif user_text == "#ลบงาน":
            if is_hr(user_id):
                # จำสถานะว่า HR กำลังจะพิมพ์เลข ID เพื่อลบงาน
                user_states[user_id] = {"state": "waiting_for_job_id"}
                reply_messages.append(
                    TextMessage(text="🗑️ โหมดลบตำแหน่งงาน\n\nกรุณาพิมพ์ 'เลข ID' ของตำแหน่งที่ต้องการลบ (เช่น 1, 2) ครับ\n*(ดูเลข ID ได้จากเมนู ดูตำแหน่งทั้งหมด)*")
                )
            else:
                reply_messages.append(TextMessage(text="❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้"))

        # ── ลบตำแหน่งงาน (HR) - ขั้นที่ 2 ดำเนินการลบ ─────────────────
        elif user_id in user_states and user_states[user_id].get("state") == "waiting_for_job_id":
            job_id_to_delete = user_text.strip()
            
            # เช็คก่อนว่า HR พิมพ์มาเป็นตัวเลขไหม
            if not job_id_to_delete.isdigit():
                reply_messages.append(TextMessage(text="❌ กรุณาพิมพ์เลข ID เป็นตัวเลขเท่านั้นครับ (เช่น 1)"))
            else:
                conn = sqlite3.connect('resume_bot.db')
                cursor = conn.cursor()
                
                # ลบข้อมูลออกจากฐานข้อมูล (หรือถ้าอยากแค่เปลี่ยน status ก็ใช้ UPDATE แทนได้ครับ)
                cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id_to_delete,))
                conn.commit()
                
                # เช็คว่าลบสำเร็จไหม (มีแถวที่ถูกลบไปกี่แถว)
                row_deleted = cursor.rowcount 
                conn.close()
                
                # ลบความจำบอททิ้ง
                del user_states[user_id]
                
                if row_deleted > 0:
                    reply_messages.append(TextMessage(text=f"✅ ลบตำแหน่งงาน ID: {job_id_to_delete} ออกจากระบบเรียบร้อยแล้ว!"))
                else:
                    reply_messages.append(TextMessage(text=f"❌ ไม่พบตำแหน่งงาน ID: {job_id_to_delete} ในระบบครับ หรืออาจถูกลบไปแล้ว"))

        # ── Default ───────────────────────────────
        else:
            reply_messages.append(
                TextMessage(text=f"FastAPI ได้รับข้อความ: {user_text}")
            )

        if reply_messages:
            api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=reply_messages,
                )
            )


# ─────────────────────────────────────────────
# Handler: ไฟล์ (File)
# ─────────────────────────────────────────────
@handler.add(MessageEvent, message=FileMessageContent)
def handle_file(event):
    message_id = event.message.id
    file_name  = event.message.file_name
    user_id    = event.source.user_id

    with ApiClient(configuration) as api_client:
        api      = MessagingApi(api_client)
        blob_api = MessagingApiBlob(api_client)

        # 1. เช็กว่า User คนนี้กำลังอยู่ในขั้นตอน "รอส่ง Resume" หรือเปล่า?
        if user_id not in user_states or user_states[user_id].get("state") != "waiting_for_resume":
            api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[TextMessage(text="ถ้าต้องการสมัครงาน ให้กดปุ่ม 'สมัครตำแหน่งนี้' จากเมนู 'ดูตำแหน่งงาน' ก่อนนะครับ 😊")]
                )
            )
            return

        # 2. เช็กนามสกุลไฟล์ว่าเป็น .pdf ไหม (กันคนส่งรูปหรือไฟล์แปลกๆ มา)
        if not file_name.lower().endswith('.pdf'):
            api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[TextMessage(text="กรุณาส่งเป็นไฟล์ .pdf ภาษาอังกฤษเท่านั้นนะครับ 📄")]
                )
            )
            return

        try:
            file_content = blob_api.get_message_content(message_id)
            save_path = os.path.join(UPLOAD_DIR, f"{user_id}_{file_name}")
            with open(save_path, "wb") as f:
                f.write(file_content)

            # 🌟 เรียก AI ของเพื่อนมาทำงาน (ดึงชื่อ อีเมล เบอร์โทร)
            job_id = user_states[user_id]["apply_for"]
            confirm_text = process_resume_from_line(user_id, save_path, job_id)
            
            reply_text = confirm_text
            
            # เปลี่ยนสถานะผู้ใช้เป็น "รอการยืนยัน"
            user_states[user_id]["state"] = "waiting_for_confirm"

        except Exception as e:
            reply_text = f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}"
            if user_id in user_states:
                del user_states[user_id] # ลบสถานะทิ้งถ้าพัง

        api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )

# ─────────────────────────────────────────────
# Handler: ผู้ใช้กดเพิ่มเพื่อน (Follow)
# ─────────────────────────────────────────────
@handler.add(FollowEvent)
def handle_follow(event):
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        
        # ส่ง Flex Menu ไปทักทายตอนแอดมาครั้งแรกเลย
        api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[
                    FlexMessage(
                        alt_text="ยินดีต้อนรับสู่ระบบรับสมัครงาน",
                        contents=flex_main_menu()
                    )
                ]
            )
        )