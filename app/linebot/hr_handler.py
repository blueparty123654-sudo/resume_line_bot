import sqlite3
import json
from linebot.v3.messaging import FlexContainer, TextMessage, FlexMessage

DB_PATH = 'resume_bot.db'

# ─────────────────────────────────────────────
# 1. ตรวจสอบสิทธิ์ HR
# ─────────────────────────────────────────────
def is_hr(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE line_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return True if result and result[0] == 'hr' else False

# ─────────────────────────────────────────────
# 2. เมนูแอดมิน (HR Menu)
# ─────────────────────────────────────────────
def flex_hr_menu():
    flex_dict = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#191919",
            "contents": [
                {
                    "type": "text", "text": "🛠️ HR Management", 
                    "color": "#FFFFFF", "weight": "bold", "size": "lg"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#1DB446",
                    "action": {
                        "type": "message",
                        "label": "📋 ดูสถานะตำแหน่งงาน",
                        "text": "#สถานะงาน"
                    }
                },
                {
                    "type": "text", "text": "💡 กดปุ่ม 'เปิดรับ' หรือ 'ปิดรับ' ในการ์ดแต่ละตำแหน่งเพื่อเปลี่ยนสถานะ",
                    "size": "xs", "color": "#888888", "wrap": True, "margin": "md", "align": "center"
                }
            ]
        }
    }
    return FlexContainer.from_dict(flex_dict)

# ─────────────────────────────────────────────
# 3. สร้าง Flex Carousel สำหรับสถานะงาน
# ─────────────────────────────────────────────
def flex_job_status_carousel(jobs_data, jobs_status_map):
    bubbles = []

    for job_id, job_info in jobs_data.items():
        is_active = jobs_status_map.get(job_id, 1)
        
        if is_active == 1:
            status_text, status_color, badge_bg = "🟢 เปิดรับสมัคร", "#1DB446", "#E8F8EC"
            btn_label, btn_color, cmd_text = "ปิดรับสมัคร", "#FF4444", f"#ปิด {job_id}"
        else:
            status_text, status_color, badge_bg = "🔴 ปิดรับสมัคร", "#FF4444", "#FDEAEA"
            btn_label, btn_color, cmd_text = "เปิดรับสมัคร", "#1DB446", f"#เปิด {job_id}"

        bubble = {
            "type": "bubble",
            "size": "micro", 
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "15px",
                "contents": [
                    {
                        "type": "text", "text": job_info.get("title", job_id),
                        "weight": "bold", "size": "md", "color": "#1DB446", "wrap": True
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "box", "layout": "vertical", "flex": 0, "backgroundColor": badge_bg,
                                "cornerRadius": "10px", "paddingStart": "8px", "paddingEnd": "8px",
                                "paddingTop": "4px", "paddingBottom": "4px",
                                "contents": [
                                    {"type": "text", "text": status_text, "size": "xxs", "color": status_color, "weight": "bold"}
                                ]
                            },
                            {
                                "type": "text", "text": f"ID: {job_id[:10]}...", 
                                "size": "xxs", "color": "#AAAAAA", "align": "end", "gravity": "center"
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingTop": "none",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": btn_color,
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": btn_label,
                            "text": cmd_text
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)

    return FlexContainer.from_dict({"type": "carousel", "contents": bubbles})

# ─────────────────────────────────────────────
# 4. จัดการคำสั่งของ HR
# ─────────────────────────────────────────────
def process_hr_message(user_text, user_id, reply_messages):
    # สมัครเป็น HR (สำหรับทดสอบ)
    # if user_text == "#ตั้งฉันเป็นแอดมิน":
        # conn = sqlite3.connect(DB_PATH)
        # conn.execute("INSERT OR IGNORE INTO users (line_id, role) VALUES (?, 'user')", (user_id,))
        # conn.execute("UPDATE users SET role = 'hr' WHERE line_id = ?", (user_id,))
        # conn.commit()
        # conn.close()
        # reply_messages.append(TextMessage(text="✅ บันทึกสิทธิ์ HR ให้คุณเรียบร้อยแล้ว!\n\nพิมพ์ 'เมนูแอดมิน' เพื่อใช้งานครับ"))
        # return True

    # ตรวจสอบว่าเป็นคำสั่ง HR ไหม
    is_hr_action = user_text in ["#สถานะงาน"] or user_text.startswith(("#เปิด ", "#ปิด "))
    if is_hr_action:
        if not is_hr(user_id):
            reply_messages.append(TextMessage(text="❌ ขออภัยครับ คุณไม่มีสิทธิ์เข้าถึงส่วนนี้"))
            return True

        # โหลดไฟล์ Jobs.json
        try:
            with open("Jobs.json", encoding="utf-8") as f:
                jobs_data = json.load(f)
        except FileNotFoundError:
            with open("jobs.json", encoding="utf-8") as f:
                jobs_data = json.load(f)

        # คำสั่งดูสถานะงาน
        if user_text == "#สถานะงาน":
            conn = sqlite3.connect(DB_PATH)
            jobs_status_map = {}
            for job_id in jobs_data:
                cursor = conn.execute("SELECT is_active FROM jobs_status WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                jobs_status_map[job_id] = row[0] if row else 1
            conn.close()

            reply_messages.append(FlexMessage(
                alt_text="📊 สถานะตำแหน่งงาน",
                contents=flex_job_status_carousel(jobs_data, jobs_status_map)
            ))
            return True

        # คำสั่งเปิด/ปิดงาน
        elif user_text.startswith(("#เปิด ", "#ปิด ")):
            parts = user_text.split(" ")
            if len(parts) < 2:
                reply_messages.append(TextMessage(text="❌ กรุณาระบุรหัสงาน เช่น #เปิด JOB001"))
                return True

            action = parts[0]
            target_job_id = parts[1].strip()

            if target_job_id not in jobs_data:
                reply_messages.append(TextMessage(text=f"❌ ไม่พบรหัสงาน '{target_job_id}' ในระบบครับ"))
                return True

            new_status = 1 if action == "#เปิด" else 0
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT OR IGNORE INTO jobs_status (job_id, is_active) VALUES (?, 1)", (target_job_id,))
            conn.execute("UPDATE jobs_status SET is_active = ? WHERE job_id = ?", (new_status, target_job_id))
            conn.commit()
            
            # โหลดสถานะงานใหม่เพื่ออัปเดต Carousel
            jobs_status_map = {}
            for job_id in jobs_data:
                cursor = conn.execute("SELECT is_active FROM jobs_status WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                jobs_status_map[job_id] = row[0] if row else 1
            conn.close()

            status_word = "🟢 เปิดรับสมัคร" if new_status == 1 else "🔴 ปิดรับสมัคร"
            reply_messages.append(TextMessage(
                text=f"✅ อัปเดตสำเร็จ!\n\nตำแหน่ง: {jobs_data[target_job_id]['title']}\nสถานะใหม่: {status_word}"
            ))
            reply_messages.append(FlexMessage(
                alt_text="📊 สถานะตำแหน่งงาน (อัปเดตแล้ว)",
                contents=flex_job_status_carousel(jobs_data, jobs_status_map)
            ))
            return True

    return False