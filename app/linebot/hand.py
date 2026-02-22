import json
import sqlite3
from linebot.v3.messaging import FlexContainer

def flex_main_menu():
    bubble = {
        "type": "bubble",
        "size": "mega",

        # 🔹 รูปด้านบน (Hero)
        "hero": {
                "type": "image",
                "url": "https://i.ibb.co/MDDvYYxq/Chat-GPT-Image-21-2569-21-51-14.png",  # 👈 เปลี่ยนเป็นรูปที่คุณต้องการ
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover",
                "cornerRadius": "20px"
                },

        # 🔹 โลโก้ลอย
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "lg",
            "paddingAll": "20px",
            "backgroundColor": "#E8F5E9",
            "contents": [


                {
                    "type": "text",
                    "text": "RESUME AI",
                    "weight": "bold",
                    "size": "lg",
                    "align": "center",
                    "margin": "md",
                    "color": "#0F5C2E"
                },

                {
                    "type": "text",
                    "text": "📌 เมนูหลัก",
                    "weight": "bold",
                    "size": "xl",
                    "align": "center",
                    "margin": "sm",
                    "color": "#1DB446"
                },

                corporate_button("ดูตำแหน่งงาน", "ดูตำแหน่งงาน"),
                corporate_button("ดูประวัติการสมัคร", "ดูประวัติการสมัคร"),
                corporate_button("วิธีการใช้งาน", "วิธีการใช้งาน"),
                corporate_button("ติดต่อเจ้าหน้าที่", "ติดต่อเจ้าหน้าที่")
            ]
        }
    }

    return FlexContainer.from_dict(bubble)


def corporate_button(label, text):
    return {
        "type": "button",
        "style": "primary",
        "height": "md",
        "color": "#1DB446",
        "action": {
            "type": "message",
            "label": label,
            "text": text
        }
    }
def flex_jobs():
    # ... (โค้ด flex_jobs เดิม ดึงจาก Jobs.json และเช็ก status เปิด-ปิด)
    try:
        with open('Jobs.json', encoding='utf-8') as f: # ใช้ตัว J ใหญ่ให้ตรงกับไฟล์คุณ
            jobs_data = json.load(f)
    except FileNotFoundError:
        with open('jobs.json', encoding='utf-8') as f:
            jobs_data = json.load(f)
        
    conn = sqlite3.connect('resume_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, is_active FROM jobs_status")
    db_status = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    
    contents = []
    for job_id, job in jobs_data.items():
        if job_id in db_status and db_status[job_id] == 0:
            continue
            
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": job["title"], "weight": "bold", "size": "xl", "color": "#1DB446"},
                    {"type": "text", "text": f"ประสบการณ์: {job['min_experience_years']} ปี", "size": "sm", "margin": "md"},
                    {"type": "text", "text": f"ทักษะ: {', '.join(job['must_have_skills'][:3])}", "size": "sm"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "message",
                            "label": "สมัครตำแหน่งนี้",
                            "text": f"สนใจสมัครตำแหน่ง: {job_id}"
                        }
                    }
                ]
            }
        }
        contents.append(bubble)

    if not contents:
         return FlexContainer.from_dict({
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "ขออภัยครับ", "weight": "bold", "size": "xl", "color": "#FF334B"},
                    {"type": "text", "text": "ขณะนี้ยังไม่มีตำแหน่งงานที่เปิดรับสมัคร", "wrap": True, "margin": "md"}
                ]
            }
        })
    return FlexContainer.from_dict({"type": "carousel", "contents": contents})

def flex_contact():
    # ... (โค้ด flex_contact เดิม)
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "📞 ติดต่อ HR", "weight": "bold", "size": "xl", "color": "#000000"},
                {"type": "text", "text": "อีเมล: hr@company.com", "size": "sm", "margin": "md"},
                {"type": "text", "text": "โทร: 02-XXX-XXXX", "size": "sm"}
            ]
        }
    }
    return FlexContainer.from_dict(bubble)

# =========================================================
# 🌟 ฟังก์ชันใหม่: ดึงประวัติการสมัครงานของผู้ใช้คนนั้น
# =========================================================
def flex_application_history(user_id):
    conn = sqlite3.connect('resume_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # ดึงข้อมูลประวัติการสมัคร จำกัดแค่ 10 อันดับล่าสุด
    cursor.execute("SELECT job_id, score, status FROM applicants WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    # ถ้าไม่เคยสมัครเลย
    if not rows:
        return FlexContainer.from_dict({
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📭 ยังไม่มีประวัติ", "weight": "bold", "size": "xl", "color": "#FF8C00"},
                    {"type": "text", "text": "คุณยังไม่เคยส่งประวัติสมัครงานเลยครับ รีบไปดูตำแหน่งงานที่เปิดรับกันเลย!", "wrap": True, "margin": "md"}
                ]
            }
        })

    # ดึงชื่อตำแหน่งงานจากไฟล์ JSON มาโชว์ให้สวยๆ
    jobs_data = {}
    try:
        with open('Jobs.json', encoding='utf-8') as f:
            jobs_data = json.load(f)
    except FileNotFoundError:
        try:
            with open('jobs.json', encoding='utf-8') as f:
                jobs_data = json.load(f)
        except FileNotFoundError:
            pass # เผื่อไฟล์ JSON หาย โค้ดจะได้ไม่พัง

    contents = []
    for row in rows:
        # 🛡️ ดักจับและแปลงค่า None ให้เป็น String ทั้งหมด ป้องกัน Error 400
        raw_job_id = row['job_id']
        job_id = str(raw_job_id) if raw_job_id else "ไม่ระบุตำแหน่ง"
        
        # ค้นหาชื่อจาก JSON ถ้าไม่มีให้ใช้คำว่า "ไม่ระบุตำแหน่ง"
        job_title = str(jobs_data.get(job_id, {}).get("title", job_id))
        if not job_title or job_title.lower() == "none":
            job_title = "ไม่ระบุตำแหน่ง"

        raw_status = row['status']
        status = str(raw_status) if raw_status else "unknown"

        raw_score = row['score']
        score = str(raw_score) if raw_score is not None else "-"

        # เปลี่ยนสถานะภาษาอังกฤษให้เป็นภาษาไทยที่เข้าใจง่าย
        if status == 'confirmed':
            status_text = "ส่งให้ HR แล้ว ✅"
            status_color = "#1DB446"
        elif status == 'waiting_confirm':
            status_text = "รอคุณยืนยัน ⏳"
            status_color = "#F5A623"
        elif status == 'rejected':
            status_text = "ไม่ผ่านเกณฑ์ ❌"
            status_color = "#FF334B"
        else:
            status_text = status
            status_color = "#666666"

        bubble = {
            "type": "bubble",
            "size": "micro", # การ์ดขนาดเล็กแบบเลื่อนซ้ายขวาได้
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": job_title, "weight": "bold", "size": "sm", "wrap": True, "color": "#000000"},
                    {"type": "text", "text": f"สถานะ: {status_text}", "size": "xs", "color": status_color, "margin": "sm"},
                    {"type": "text", "text": f"คะแนนจาก AI: {score}/100", "size": "xs", "color": "#888888", "margin": "xs"}
                ]
            }
        }
        contents.append(bubble)

    return FlexContainer.from_dict({"type": "carousel", "contents": contents})