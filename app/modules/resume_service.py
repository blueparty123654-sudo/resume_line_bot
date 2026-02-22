# modules/resume_service.py

import os
from app.modules.resume_logic import extract_basic_info_only
from app.database import save_to_db

# ─────────────────────────────────────────────
# จัดการการประมวลผล Resume เบื้องต้น
# ─────────────────────────────────────────────
def process_resume_from_line(user_id: str, file_path: str, job_id: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError("ไม่พบไฟล์ PDF")

    if not file_path.lower().endswith(".pdf"):
        raise ValueError("รองรับเฉพาะไฟล์ PDF เท่านั้น")

    # 1. ดึงข้อมูลพื้นฐานจาก PDF
    basic_info = extract_basic_info_only(file_path, job_id)

    # 2. บันทึกข้อมูลเบื้องต้นและรอการยืนยัน
    basic_info["raw_result"]["status"] = "waiting_confirm"
    save_to_db(
        user_id=user_id,
        result=basic_info["raw_result"],
        temp_file_path=file_path 
    )

    # 3. ส่งข้อความแจ้งให้ผู้ใช้ตรวจสอบ
    confirm_text = (
        "กรุณาตรวจสอบข้อมูลของคุณ:\n\n"
        f"ชื่อ: {basic_info['full_name']}\n"
        f"Email: {basic_info['email']}\n"
        f"เบอร์โทร: {basic_info['phone']}\n\n"
        "หากถูกต้อง พิมพ์: ถูกต้อง\n"
        "หากต้องการแก้ไข พิมพ์: แก้ไข"
    )

    return confirm_text