import sqlite3
from linebot.v3.messaging import FlexContainer

# ==========================================
# 3. ฟังก์ชันสร้างการ์ดเมนูสำหรับ HR (แอดมิน)
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
                        "label": "➕ สร้างตำแหน่งงาน",
                        "text": "#สร้างงาน"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "message",
                        "label": "📋 ดูตำแหน่งทั้งหมด",
                        "text": "#ดูงานแอดมิน"
                    }
                },
                {
                    "type": "button",
                    "style": "link",
                    "color": "#FF334B",
                    "action": {
                        "type": "message",
                        "label": "🗑️ ลบ/ปิดรับสมัคร",
                        "text": "#ลบงาน"
                    }
                }
            ]
        }
    }
    return FlexContainer.from_dict(flex_dict)