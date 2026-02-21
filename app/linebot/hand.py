import json
import sqlite3
from linebot.v3.messaging import FlexContainer


# =========================
# 1️⃣ MAIN MENU
# =========================
def flex_main_menu():
    flex_dict = {
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": "https://images.unsplash.com/photo-1586281380349-632531db7ed4?q=80&w=800&auto=format&fit=crop",
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "ระบบรับสมัครงานอัตโนมัติ",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#1DB446",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": "เลือกเมนูด้านล่างเพื่อดูตำแหน่งงาน หรือสอบถามข้อมูลเพิ่มเติมครับ 👇",
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True
                }
            ]
        },
        "footer": {
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
                        "label": "ดูตำแหน่งงาน 💼",
                        "text": "ดูตำแหน่งงาน"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "message",
                        "label": "วิธีการใช้งาน 📖",
                        "text": "วิธีการใช้งาน"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "message",
                        "label": "ติดต่อเรา 📞",
                        "text": "ติดต่อเจ้าหน้าที่"
                    }
                }
            ]
        }
    }
    return FlexContainer.from_dict(flex_dict)


# =========================
# 2️⃣ JOB LIST (Carousel)
# =========================
def flex_jobs():
    # อ่านไฟล์ jobs.json
    with open('jobs.json', encoding='utf-8') as f:
        jobs_data = json.load(f)
    
    contents = []
    for job_id, job in jobs_data.items():
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
                            "text": f"สนใจสมัครตำแหน่ง: {job_id}" # ส่ง job_id (เช่น dev_backend) กลับมาให้บอท
                        }
                    }
                ]
            }
        }
        contents.append(bubble)

    return FlexContainer.from_dict({"type": "carousel", "contents": contents})

    bubbles = []
    for job in jobs:
        title = job[1]
        requirements = job[2]

        bubble = {
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "xl",
                        "wrap": True,
                        "color": "#1DB446"
                    },
                    {
                        "type": "text",
                        "text": "ทักษะที่ต้องการ:",
                        "size": "sm",
                        "weight": "bold",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": requirements,
                        "size": "sm",
                        "color": "#666666",
                        "wrap": True
                    }
                ]
            },
            "footer": {
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
                            "label": "สมัครตำแหน่งนี้",
                            "text": f"สนใจสมัครตำแหน่ง: {title}"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "message",
                            "label": "สอบถามเกี่ยวกับงานนี้",
                            "text": f"สอบถามรายละเอียดตำแหน่ง: {title}"
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)

    carousel_flex = {
        "type": "carousel",
        "contents": bubbles
    }

    return FlexContainer.from_dict(carousel_flex)


# =========================
# 3️⃣ CONTACT FLEX
# =========================
def flex_contact():
    contact_flex = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "ติดต่อฝ่าย HR",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#1DB446"
                },
                {
                    "type": "text",
                    "text": "📧 hr@company.com\n📞 02-123-4567\n⏰ จันทร์ - ศุกร์ 09:00 - 18:00",
                    "size": "sm",
                    "wrap": True
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#1DB446",
                    "action": {
                        "type": "uri",
                        "label": "ส่งอีเมลหา HR",
                        "uri": "mailto:hr@company.com"
                    }
                }
            ]
        }
    }

    return FlexContainer.from_dict(contact_flex)