import sqlite3
import json
from linebot.v3.messaging import (
    FlexContainer, TextMessage, FlexMessage
)

DB_PATH = 'resume_bot.db'

# ==========================================
# 1. เช็กว่าเป็น HR ไหม
# ==========================================
def is_hr(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE line_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0] == 'hr':
        return True
    return False

# ==========================================
# 2. การ์ดเมนูแอดมิน (HR Menu)
# ==========================================
def flex_hr_menu():
    flex_dict = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#191919",
            "contents": [
                {
                    "type": "text",
                    "text": "🛠️ HR Management",
                    "color": "#FFFFFF",
                    "weight": "bold",
                    "size": "lg"
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
                    "type": "text",
                    "text": "💡 กดปุ่ม 'เปิดรับ' หรือ 'ปิดรับ' ในการ์ดแต่ละตำแหน่งเพื่อเปลี่ยนสถานะ",
                    "size": "xs",
                    "color": "#888888",
                    "wrap": True,
                    "margin": "md",
                    "align": "center"
                }
            ]
        }
    }
    return FlexContainer.from_dict(flex_dict)

# ==========================================
# 3. สร้าง Flex Carousel สำหรับสถานะงาน
# ==========================================
def flex_job_status_carousel(jobs_data, jobs_status_map):
    """
    สร้าง Flex Message แบบ Carousel ที่มีการ์ดสำหรับแต่ละตำแหน่ง
    ดีไซน์แบบมินิมอล มีแค่ชื่อตำแหน่ง ป้ายสถานะ และปุ่มเปิด/ปิด
    """
    bubbles = []

    for job_id, job_info in jobs_data.items():
        is_active = jobs_status_map.get(job_id, 1)
        
        # จัดการข้อความและสีตามสถานะปัจจุบัน
        if is_active == 1:
            status_text = "🟢 เปิดรับสมัคร"
            status_color = "#1DB446"
            badge_bg = "#E8F8EC"
            # ปุ่มตรงข้าม (เพื่อกดปิด)
            btn_label = "ปิดรับสมัคร"
            btn_color = "#FF4444"
            cmd_text = f"#ปิด {job_id}"
        else:
            status_text = "🔴 ปิดรับสมัคร"
            status_color = "#FF4444"
            badge_bg = "#FDEAEA"
            # ปุ่มตรงข้าม (เพื่อกดเปิด)
            btn_label = "เปิดรับสมัคร"
            btn_color = "#1DB446"
            cmd_text = f"#เปิด {job_id}"

        bubble = {
            "type": "bubble",
            "size": "micro", # ใช้การ์ดขนาดเล็กเพื่อให้เลื่อนดูได้ง่าย
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "15px",
                "contents": [
                    {
                        "type": "text",
                        "text": job_info.get("title", job_id),
                        "weight": "bold",
                        "size": "md",
                        "color": "#1DB446",
                        "wrap": True
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "flex": 0,
                                "backgroundColor": badge_bg,
                                "cornerRadius": "10px",
                                "paddingStart": "8px",
                                "paddingEnd": "8px",
                                "paddingTop": "4px",
                                "paddingBottom": "4px",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": status_text,
                                        "size": "xxs",
                                        "color": status_color,
                                        "weight": "bold"
                                    }
                                ]
                            },
                            {
                                "type": "text",
                                "text": f"ID: {job_id[:10]}...", # ตัด ID ให้สั้นลงถ้าจำเป็น
                                "size": "xxs",
                                "color": "#AAAAAA",
                                "align": "end",
                                "gravity": "center"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": "ไม่มีรายละเอียดเพิ่มเติม",
                        "size": "xs",
                        "color": "#AAAAAA",
                        "margin": "md"
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

    carousel = {
        "type": "carousel",
        "contents": bubbles
    }

    return FlexContainer.from_dict(carousel)

# ==========================================
# 4. จัดการคำสั่งของ HR (Logic If-Else)
# ==========================================
def process_hr_message(user_text, user_id, reply_messages):
    """
    คืนค่า True ถ้าเป็นคำสั่ง HR (จะจบการทำงาน ไม่ไปหา User ปกติ)
    """

    # ── 1. ตั้งเป็น HR ─────────────────────────
    if user_text == "#ตั้งฉันเป็นแอดมิน":
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO users (line_id, role) VALUES (?, 'user')",
            (user_id,)
        )
        conn.execute(
            "UPDATE users SET role = 'hr' WHERE line_id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()

        reply_messages.append(
            TextMessage(
                text="✅ บันทึกสิทธิ์ HR ให้คุณเรียบร้อยแล้ว!\n\nพิมพ์ 'เมนูแอดมิน' เพื่อใช้งานครับ"
            )
        )
        return True

    # ── 2. ตรวจสอบว่าเป็นคำสั่ง HR ไหม ─────────────────────────
    hr_commands = ["#สถานะงาน"]
    is_hr_action = (
        user_text in hr_commands
        or user_text.startswith("#เปิด ")
        or user_text.startswith("#ปิด ")
    )

    if is_hr_action:
        if not is_hr(user_id):
            reply_messages.append(
                TextMessage(text="❌ ขออภัยครับ คุณไม่มีสิทธิ์เข้าถึงส่วนนี้")
            )
            return True

    # ── 3. ดูสถานะงาน (Flex Carousel) ─────────────────────────
    if user_text == "#สถานะงาน":
        with open("jobs.json", encoding="utf-8") as f:
            jobs_data = json.load(f)

        conn = sqlite3.connect(DB_PATH)
        jobs_status_map = {}
        for job_id in jobs_data:
            cursor = conn.execute(
                "SELECT is_active FROM jobs_status WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
            jobs_status_map[job_id] = row[0] if row else 1
        conn.close()

        carousel_container = flex_job_status_carousel(jobs_data, jobs_status_map)

        reply_messages.append(
            FlexMessage(
                alt_text="📊 สถานะตำแหน่งงาน",
                contents=carousel_container
            )
        )
        return True

    # ── 4. เปิด / ปิด งาน ─────────────────────────
    if user_text.startswith("#เปิด ") or user_text.startswith("#ปิด "):

        parts = user_text.split(" ")

        if len(parts) < 2:
            reply_messages.append(
                TextMessage(text="❌ กรุณาระบุรหัสงาน เช่น #เปิด JOB001")
            )
            return True

        action = parts[0]
        target_job_id = parts[1].strip()

        with open("jobs.json", encoding="utf-8") as f:
            jobs_data = json.load(f)

        if target_job_id not in jobs_data:
            reply_messages.append(
                TextMessage(
                    text=f"❌ ไม่พบรหัสงาน '{target_job_id}' ในระบบครับ"
                )
            )
            return True

        new_status = 1 if action == "#เปิด" else 0

        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO jobs_status (job_id, is_active) VALUES (?, 1)",
            (target_job_id,)
        )
        conn.execute(
            "UPDATE jobs_status SET is_active = ? WHERE job_id = ?",
            (new_status, target_job_id)
        )
        conn.commit()
        conn.close()

        status_word = (
            "🟢 เปิดรับสมัคร" if new_status == 1 else "🔴 ปิดรับสมัคร"
        )

        # อัปเดตสำเร็จ → แสดง Carousel ใหม่ให้ด้วย
        reply_messages.append(
            TextMessage(
                text=f"✅ อัปเดตสำเร็จ!\n\nตำแหน่ง: {jobs_data[target_job_id]['title']}\nสถานะใหม่: {status_word}"
            )
        )

        # Refresh carousel
        conn = sqlite3.connect(DB_PATH)
        jobs_status_map = {}
        for job_id in jobs_data:
            cursor = conn.execute(
                "SELECT is_active FROM jobs_status WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
            jobs_status_map[job_id] = row[0] if row else 1
        conn.close()

        carousel_container = flex_job_status_carousel(jobs_data, jobs_status_map)
        reply_messages.append(
            FlexMessage(
                alt_text="📊 สถานะตำแหน่งงาน (อัปเดตแล้ว)",
                contents=carousel_container
            )
        )
        return True

    return False