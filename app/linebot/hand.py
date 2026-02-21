from linebot.v3.messaging import FlexContainer

def flex_menu():
    # สร้างตัวแปรเก็บ Dictionary ของ Flex Message ไว้ก่อน
    flex_dict = {
        "type": "carousel",
        "contents": [
            # ========= CARD 1 =========
            {
                "type": "bubble",
                "size": "mega",
                "hero": {
                    "type": "image",
                    "url": "https://picsum.photos/800/800?1",
                    "size": "full",
                    "aspectMode": "cover",
                    "aspectRatio": "1:1"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "เขียน Resume อย่างไรให้ปัง",
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": "เทคนิคทำ Resume ให้ HR หยุดอ่าน",
                            "size": "sm",
                            "color": "#666666",
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
                            "action": {
                                "type": "uri",
                                "label": "อ่านบทความ",
                                "uri": "https://google.com"
                            }
                        }
                    ]
                }
            },
            # ========= CARD 2 =========
            {
                "type": "bubble",
                "size": "mega",
                "hero": {
                    "type": "image",
                    "url": "https://picsum.photos/800/800?2",
                    "size": "full",
                    "aspectMode": "cover",
                    "aspectRatio": "1:1"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "เตรียมตัวสัมภาษณ์งาน",
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": "คำถามยอดฮิตที่ต้องเจอแน่นอน",
                            "size": "sm",
                            "color": "#666666",
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
                            "action": {
                                "type": "uri",
                                "label": "ดูเพิ่มเติม",
                                "uri": "https://google.com"
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    # แปลง dict ให้กลายเป็น FlexContainer Object ก่อน Return กลับไป
    return FlexContainer.from_dict(flex_dict)