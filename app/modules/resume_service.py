# modules/resume_service.py

import os
from app.modules.resume_logic import extract_basic_info_only
from app.database import save_to_db
def process_resume_from_line(user_id: str, file_path: str, job_id: str):

    if not os.path.exists(file_path):
        raise FileNotFoundError("ไม่พบไฟล์ PDF")

    if not file_path.lower().endswith(".pdf"):
        raise ValueError("รองรับเฉพาะไฟล์ PDF เท่านั้น")

    # 1️⃣ ดึงข้อมูลพื้นฐานก่อน
    basic_info = extract_basic_info_only(file_path, job_id)

    # 2️⃣ บันทึกสถานะรอ confirm
    basic_info["raw_result"]["status"] = "waiting_confirm" # ยัด status ลงไปในนี้แทน
    save_to_db(
        user_id=user_id,
        result=basic_info["raw_result"],
        temp_file_path=file_path # แก้ชื่อ parameter จาก file_path เป็น temp_file_path ให้ตรงกับ database.py
    )

    # 3️⃣ ส่งข้อความกลับไปถามผู้ใช้
    confirm_text = f"""
กรุณาตรวจสอบข้อมูลของคุณ:

ชื่อ: {basic_info['full_name']}
Email: {basic_info['email']}
เบอร์โทร: {basic_info['phone']}

หากถูกต้อง พิมพ์: ถูกต้อง
หากต้องการแก้ไข พิมพ์: แก้ไข
"""

    return confirm_text