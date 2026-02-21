"""
modules/resume_logic.py
========================
Resume Scoring Engine — LLM Version (Gemini AI)

รองรับหลายตำแหน่งงาน กำหนดเกณฑ์ผ่าน jobs.json
Gemini อ่านและวิเคราะห์ Resume แทนการนับ keyword เอง
"""

import json #อ่านและเขียนไฟล์ JSON
import logging #แสดงผล log debug และ error
from pathlib import Path #เช็คว่าไฟล์มีอยู่จริงไหม

import google.generativeai as genai    #ใช้เรียก Gemini API
import pdfplumber   #ใช้อ่านไฟล์

logging.basicConfig(level=logging.INFO) #ไว้แสดง log 
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
# CONFIG — ใส่ API Key ที่นี่
# ══════════════════════════════════════════════════════════

GEMINI_API_KEY = "AIzaSyC_5YjJoZdtCEA08sKcKISxwBVQ4guvYac"

# ══════════════════════════════════════════════════════════
# STEP 1: อ่าน PDF
# ══════════════════════════════════════════════════════════

def extract_text_from_pdf(file_path: str) -> str: #เปิดไฟล์ PDF แล้วแกะข้อความออกมาทีละหน้าเป็น String เดียว
    path = Path(file_path) #Check ว่าไฟล์มีอยู่จริงไหม
    if not path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์: {file_path}")

    pages = []
    with pdfplumber.open(file_path) as pdf: #เปิดไฟล์ PDF และอ่านทีละหน้า
        logger.info(f"PDF: {len(pdf.pages)} หน้า")
        for i, page in enumerate(pdf.pages, 1): #ถ้าหน้านั้นมีข้อความก็เก็บไว้ ถ้าไม่มีข้อความก็แสดง warning
            text = page.extract_text()
            if text:
                pages.append(text)
            else:
                logger.warning(f"หน้า {i} ไม่มีข้อความ")

    full_text = "\n".join(pages).strip() #รวมทุกหน้าเป็น String เดียว
    if not full_text: #ถ้าไม่มีข้อความเลยก็แสดง error
        raise ValueError("PDF ไม่มีข้อความ (อาจเป็น scanned image ที่ไม่มี OCR)")

    logger.info(f"อ่านข้อความได้ {len(full_text)} ตัวอักษร")
    return full_text


# ══════════════════════════════════════════════════════════
# STEP 2: โหลด Job Config
# ══════════════════════════════════════════════════════════

def load_job_config(job_id: str, config_path: str = "jobs.json") -> dict: #เปิด Json แล้วดึงเกณฑ์ของตำแหน่งงานที่ต้องการออกมา
    with open(config_path, encoding="utf-8") as f:#อ่านไฟล์
        jobs = json.load(f)
    if job_id not in jobs: 
        available = list(jobs.keys())
        raise ValueError(f"ไม่พบตำแหน่ง '{job_id}' | ตำแหน่งที่มี: {available}")
    return jobs[job_id]


def list_all_jobs(config_path: str = "jobs.json") -> dict:
    """คืนรายชื่อตำแหน่งทั้งหมด"""
    with open(config_path, encoding="utf-8") as f:
        jobs = json.load(f)
    return {job_id: job["title"] for job_id, job in jobs.items()}


# ══════════════════════════════════════════════════════════
# STEP 3: ให้ gemini วิเคราะห์
# ══════════════════════════════════════════════════════════

def calculate_score(text: str, job_id: str, config_path: str = "jobs.json") -> dict: #รับข้อความ Resume และ job_id แล้วส่งให้ Gemini วิเคราะห์ตามเกณฑ์ที่กำหนดใน jobs.json
    job        = load_job_config(job_id, config_path)
    text_lower = text.lower()

    # ── Blacklist check ก่อนส่ง AI (ประหยัด API call) ───
    hits = [kw for kw in job.get("blacklist", []) if kw.lower() in text_lower]
    if hits:
        return {
            "job_id":        job_id,
            "job_title":     job["title"],
            "blacklisted":   True,
            "blacklist_hits": hits,
            "score":         0,
            "passed":        False,
            "summary":       f"❌ พบคำต้องห้าม: {', '.join(hits)} → ตัดสิทธิ์ทันที",
        }

    # ── สร้าง Prompt ──────────────────────────────────────
    prompt = f"""
คุณคือ HR ผู้เชี่ยวชาญ กำลังวิเคราะห์ Resume สำหรับตำแหน่ง "{job['title']}"

━━━ เกณฑ์การประเมิน ━━━
ทักษะที่ต้องมี (must have)   : {job.get('must_have_skills', [])}
ทักษะ Bonus (nice to have)   : {job.get('nice_to_have_skills', [])}
ประสบการณ์ขั้นต่ำ            : {job.get('min_experience_years', 0)} ปี
เกรดขั้นต่ำ                  : {job.get('min_gpa', 0)}
สาขาที่รับ                   : {job.get('accepted_degrees', [])}
คะแนนผ่านเกณฑ์              : {job.get('passing_score', 60)}/100

━━━ กฎการให้คะแนน ━━━
1. ทักษะที่ "must have" มีครบ = 60 คะแนน (เฉลี่ยตามจำนวน)
2. ทักษะ "nice to have" แต่ละอัน = +5 คะแนน (สูงสุด 20 คะแนน)
3. เกรดและวุฒิการศึกษาตรง = +10 คะแนน
4. ประสบการณ์ตรงหรือเกินกำหนด = +10 คะแนน
5. ถ้าเขียนว่า "อยากเรียน", "สนใจ", "beginner", "want to learn" ข้างๆ ทักษะใด → ทักษะนั้นไม่นับ
6. ทักษะที่เขียนต่างกันแต่ความหมายเดียวกัน เช่น "ภาษางู = Python" ให้นับด้วย

━━━ Resume ━━━
{text}

━━━ ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่น ━━━
{{
  "full_name":   "ชื่อ-นามสกุล",       
  "phone":       "เบอร์โทร",           
  "email":       "อีเมล",               
  "university":  "มหาวิทยาลัย", 
  "score": 75,
  "passed": true,
  "must_have_found":    ["Python", "SQL"],
  "must_have_missing":  ["Git"],
  "nice_to_have_found": ["Docker"],
  "gpa":                3.25,
  "gpa_pass":           true,
  "degree":             "วิทยาการคอมพิวเตอร์",
  "degree_pass":        true,
  "experience_years":   2,
  "experience_pass":    true,
  "summary":            "สรุปสั้นๆ ภาษาไทย ว่าทำไมได้คะแนนนี้",
  "recommendation":     "แนะนำสำหรับ HR ว่าควรเรียกสัมภาษณ์ไหม และเหตุผล"
}}
"""

    # ── เรียก Gemeni API ──────────────────────────────────
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model    = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # ลบ markdown code block ถ้ามี
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        result             = json.loads(raw_text)
        result["job_id"]   = job_id
        result["job_title"] = job["title"]
        result["blacklisted"] = False

        status = "✅ ผ่านเกณฑ์" if result.get("passed") else "⚠️ ไม่ผ่านเกณฑ์"
        logger.info(f"{status} | คะแนน: {result.get('score')}/100 | {job['title']}")
        return result

    except json.JSONDecodeError as e: #คืน error ถ้า AI ตอบไม่ใช่ JSON ตามที่กำหนด
        logger.error(f"Gemini ตอบไม่ใช่ JSON: {e}")
        return {"error": "AI ตอบผิดรูปแบบ กรุณาลองใหม่", "score": 0, "passed": False}

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {"error": str(e), "score": 0, "passed": False}


# ══════════════════════════════════════════════════════════
# MAIN FUNCTION — LINE handler เรียกใช้ตรงนี้
# ══════════════════════════════════════════════════════════

def process_resume(file_path: str, job_id: str, config_path: str = "jobs.json") -> dict:
    """
    ฟังก์ชันหลัก — รับ path ไฟล์ PDF และ job_id

    Usage:
        result = process_resume("/tmp/resume.pdf", "dev_backend")
        result = process_resume("/tmp/resume.pdf", "hr_officer")
        result = process_resume("/tmp/resume.pdf", "marketing")
    """
    try:
        text   = extract_text_from_pdf(file_path)
        result = calculate_score(text, job_id, config_path)
        result["text_length"] = len(text)
        return result
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"process_resume error: {e}")
        return {"error": str(e), "score": 0, "passed": False}
# ══════════════════════════════════════════════════════════
# STEP เพิ่ม: ดึงข้อมูลพื้นฐานก่อน Confirm
# ══════════════════════════════════════════════════════════

def extract_basic_info_only(file_path: str, job_id: str, config_path: str = "jobs.json") -> dict:
    """
    อ่าน Resume และดึงเฉพาะข้อมูลติดต่อ
    (ยังไม่ส่งผลผ่าน/ไม่ผ่านให้ผู้ใช้)
    """

    try:
        text = extract_text_from_pdf(file_path)
        result = calculate_score(text, job_id, config_path)

        return {
            "full_name": result.get("full_name"),
            "email": result.get("email"),
            "phone": result.get("phone"),
            "job_id": result.get("job_id"),
            "job_title": result.get("job_title"),
            "raw_result": result  # เก็บผลประเมินไว้ใช้หลัง confirm
        }

    except Exception as e:
        logger.error(f"extract_basic_info_only error: {e}")
        return {"error": str(e)}

# ══════════════════════════════════════════════════════════
# CLI TEST
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # แสดงตำแหน่งที่มีทั้งหมด
    try:
        all_jobs = list_all_jobs()
        print("\nตำแหน่งงานที่รองรับ:")
        for jid, title in all_jobs.items():
            print(f"  {jid:20s} → {title}")
        print()
    except Exception:
        pass

    if len(sys.argv) < 3:
        print("Usage: python modules/resume_logic.py <resume.pdf> <job_id>")
        print("Example:")
        print("  python modules/resume_logic.py Resume.pdf dev_backend")
        print("  python modules/resume_logic.py Resume.pdf hr_officer")
        print("  python modules/resume_logic.py Resume.pdf marketing")
        sys.exit(1)

    result = process_resume(sys.argv[1], sys.argv[2])

    print("═" * 60)
    print("  ผลการประเมิน Resume")
    print("═" * 60)

    if result.get("error"):
        print(f"  ❌ Error: {result['error']}")

    elif result.get("blacklisted"):
        print(f"  ❌ ตัดสิทธิ์ทันที!")
        print(f"  พบคำต้องห้าม: {result['blacklist_hits']}")

    else:
        status = "✅ ผ่านเกณฑ์" if result["passed"] else "⚠️ ไม่ผ่านเกณฑ์"
        print(f"  {status}")
        print(f"  ตำแหน่ง          : {result.get('job_title')}")
        print(f"  คะแนนรวม         : {result.get('score')}/100")
        print(f"  GPA              : {result.get('gpa')} ({'✅' if result.get('gpa_pass') else '❌'})")
        print(f"  สาขา             : {result.get('degree')} ({'✅' if result.get('degree_pass') else '❌'})")
        print(f"  ประสบการณ์        : {result.get('experience_years')} ปี ({'✅' if result.get('experience_pass') else '❌'})")
        print(f"  ทักษะที่มี        : {result.get('must_have_found', [])}")
        print(f"  ทักษะที่ขาด       : {result.get('must_have_missing', [])}")
        print(f"  Bonus ที่มี       : {result.get('nice_to_have_found', [])}")
        print("─" * 60)
        print(f"  สรุป    : {result.get('summary')}")
        print(f"  แนะนำ HR: {result.get('recommendation')}")

    print("═" * 60)