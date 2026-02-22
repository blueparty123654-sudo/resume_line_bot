"""
modules/resume_logic.py
========================
Resume Scoring Engine — LLM Version (Gemini AI)
"""

import json
import logging
from pathlib import Path
import google.generativeai as genai
import pdfplumber
from app.config import GEMINI_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════
genai.configure(api_key=GEMINI_API_KEY)

# ══════════════════════════════════════════════════════════
# STEP 1: อ่าน PDF
# ══════════════════════════════════════════════════════════

def extract_text_from_pdf(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์: {file_path}")

    pages = []
    with pdfplumber.open(file_path) as pdf:
        logger.info(f"PDF: {len(pdf.pages)} หน้า")
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                pages.append(text)
            else:
                logger.warning(f"หน้า {i} ไม่มีข้อความ")

    full_text = "\n".join(pages).strip()
    if not full_text:
        raise ValueError("PDF ไม่มีข้อความ (อาจเป็น scanned image ที่ไม่มี OCR)")

    logger.info(f"อ่านข้อความได้ {len(full_text)} ตัวอักษร")
    return full_text

# ══════════════════════════════════════════════════════════
# STEP 2: โหลด Job Config
# ══════════════════════════════════════════════════════════

def load_job_config(job_id: str, config_path: str = "jobs.json") -> dict:
    with open(config_path, encoding="utf-8") as f:
        jobs = json.load(f)
    if job_id not in jobs:
        available = list(jobs.keys())
        raise ValueError(f"ไม่พบตำแหน่ง '{job_id}' | ตำแหน่งที่มี: {available}")
    return jobs[job_id]

def list_all_jobs(config_path: str = "jobs.json") -> dict:
    with open(config_path, encoding="utf-8") as f:
        jobs = json.load(f)
    return {job_id: job["title"] for job_id, job in jobs.items()}

# ══════════════════════════════════════════════════════════
# STEP 3: ให้ gemini วิเคราะห์
# ══════════════════════════════════════════════════════════

def calculate_score(text: str, job_id: str, config_path: str = "jobs.json") -> dict:
    job = load_job_config(job_id, config_path)
    text_lower = text.lower()

    # Blacklist check
    hits = [kw for kw in job.get("blacklist", []) if kw.lower() in text_lower]
    if hits:
        return {
            "job_id": job_id, "job_title": job["title"], "blacklisted": True,
            "blacklist_hits": hits, "score": 0, "passed": False,
            "summary": f"❌ พบคำต้องห้าม: {', '.join(hits)} → ตัดสิทธิ์ทันที",
        }

    prompt = f"""
คุณคือ HR ผู้เชี่ยวชาญ

━━━ ภารกิจลำดับที่ 1 ━━━
ตรวจสอบว่าเนื้อหาใน "━━━ Resume ━━━" คือ "ประวัติส่วนตัวเพื่อสมัครงาน" หรือไม่?
- หากไม่ใช่ตอบ JSON: {{ "is_resume": false }}
- หากใช่ตอบ JSON: {{ "is_resume": true }} และทำภารกิจที่ 2

━━━ ภารกิจลำดับที่ 2 (วิเคราะห์คะแนน) ━━━
วิเคราะห์ Resume ตำแหน่ง "{job['title']}" ตามเกณฑ์:
เกรดขั้นต่ำ: {job.get('min_gpa', 0)}
วุฒิการศึกษาที่รับ: {', '.join(job.get('accepted_degrees', []))}
ประสบการณ์ขั้นต่ำ: {job.get('min_experience_years', 0)} ปี
ทักษะที่ต้องมี (must have): {', '.join(job.get('must_have_skills', []))}
ทักษะ Bonus (nice to have): {', '.join(job.get('nice_to_have_skills', []))}

━━━ กฎการคิดคะแนน (เต็ม 100) ━━━
1. ทักษะ "must have" มีครบ = 60 คะแนน (ถ้าขาดให้หักลบตามสัดส่วน)
2. ทักษะ "nice to have" = ทักษะละ 5 คะแนน (สูงสุด 20 คะแนน)
3. เกรดและวุฒิการศึกษาตรงตามเกณฑ์ = +10 คะแนน
4. ประสบการณ์ตรงหรือมากกว่าที่กำหนด = +10 คะแนน

━━━ Resume ━━━
{text}

━━━ ตอบเป็น JSON เท่านั้น ━━━
{{
  "is_resume": true,
  "full_name": "ชื่อ-นามสกุล",
  "phone": "เบอร์โทร",
  "email": "อีเมล",
  "university": "มหาวิทยาลัย",
  "score": 75,
  "summary": "สรุปสั้นๆ ภาษาไทย",
  "recommendation": "คำแนะนำสำหรับ HR",
  "gpa": 3.25,
  "degree": "ชื่อวุฒิการศึกษา",
  "experience_years": 2,
  "must_have_found": [],
  "must_have_missing": [],
  "nice_to_have_found": []
}}
"""

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()

    result = json.loads(raw_text)
    
    if result.get("is_resume") is False:
        return {"error": "เอกสารไม่ใช่ Resume", "is_resume": False, "score": 0, "passed": False}

    # ให้ Python เป็นคนตัดสินชี้ขาด
    ai_score = result.get("score", 0)
    passing_score = job.get("passing_score", 60)
    
    result["passed"] = bool(ai_score >= passing_score)
    result["job_id"] = job_id
    result["job_title"] = job["title"]
    result["blacklisted"] = False

    status = "✅ ผ่านเกณฑ์" if result.get("passed") else "⚠️ ไม่ผ่านเกณฑ์"
    logger.info(f"{status} | คะแนน: {ai_score}/{passing_score} | {job['title']}")
    
    return result

# ══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════

def process_resume(file_path: str, job_id: str, config_path: str = "jobs.json") -> dict:
    try:
        text = extract_text_from_pdf(file_path)
        result = calculate_score(text, job_id, config_path)
        result["text_length"] = len(text)
        return result
    except Exception as e:
        logger.exception("🔥 เกิดข้อผิดพลาดแบบเต็มๆ ใน process_resume:")
        return {"error": str(e), "score": 0, "passed": False}

def extract_basic_info_only(file_path: str, job_id: str, config_path: str = "jobs.json") -> dict:
    try:
        text = extract_text_from_pdf(file_path)
        result = calculate_score(text, job_id, config_path)
        return {
            "full_name": result.get("full_name"),
            "email": result.get("email"),
            "phone": result.get("phone"),
            "job_id": result.get("job_id"),
            "job_title": result.get("job_title"),
            "raw_result": result
        }
    except Exception as e:
        logger.exception("🔥 เกิดข้อผิดพลาดแบบเต็มๆ ใน extract_basic_info_only:")
        return {"error": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python modules/resume_logic.py <resume.pdf> <job_id>")
        sys.exit(1)
    
    try:
        res = process_resume(sys.argv[1], sys.argv[2])
        print(json.dumps(res, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")