"""
database.py
===========
รับผิดชอบ: บันทึกและดึงข้อมูลผู้สมัครจาก SQLite Database
รับข้อมูลจาก: resume_logic.py (ผลการวิเคราะห์ Resume)
บันทึก: ไฟล์ Resume, ทักษะ, เกรด, คณะ, ประสบการณ์, คะแนน
"""

import sqlite3
import shutil
import os
import json
from datetime import datetime

# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════

DB_PATH      = "resume_bot.db"      # ไฟล์ Database
RESUME = "resume/"  # โฟลเดอร์เก็บไฟล์ Resume ถาวร


# ══════════════════════════════════════════════════════════
# STEP 1: สร้าง Table
# ══════════════════════════════════════════════════════════

def init_db():
    """
    สร้าง Table 'applicants' (ของผู้สมัคร)
    และ Table 'users', 'jobs_status' (ของระบบ HR)
    """
    os.makedirs(RESUME, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    
    # 1. ตารางเก็บข้อมูลผู้สมัคร (ของเพื่อน)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          TEXT,
            full_name        TEXT,
            phone            TEXT,
            email            TEXT,
            university       TEXT,
            job_id           TEXT,
            job_title        TEXT,
            score            REAL,
            passed           INTEGER,
            gpa              REAL,
            degree           TEXT,
            gpa_pass         INTEGER,
            degree_pass      INTEGER,
            experience_years INTEGER,
            experience_pass  INTEGER,
            skills_found     TEXT,
            skills_missing   TEXT,
            bonus_found      TEXT,
            file_path        TEXT,
            summary          TEXT,
            recommendation   TEXT,
            status           TEXT,
            created_at       TEXT
        )
    """)

    # 2. ตารางจัดการสิทธิ์ HR (ของคุณ)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            line_id TEXT PRIMARY KEY,
            role TEXT DEFAULT 'user'
        )
    """)

    # 3. ตารางเปิด-ปิดตำแหน่งงาน (ของคุณ)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs_status (
            job_id TEXT PRIMARY KEY,
            is_active INTEGER DEFAULT 1  -- ค่าเริ่มต้น 1 = เปิดรับสมัคร
        )
    """)

    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════
# STEP 2: บันทึกไฟล์ Resume ถาวร
# ══════════════════════════════════════════════════════════

def save_resume_file(user_id: str, temp_file_path: str) -> str:
    """
    ย้ายไฟล์ Resume จาก path ชั่วคราว → resume/ ถาวร
    ตั้งชื่อใหม่เป็น user_id + วันเวลา

    Returns:
        str: path ถาวรของไฟล์
    """
    os.makedirs(RESUME, exist_ok=True)

    # ตั้งชื่อไฟล์ใหม่ เช่น resume/user001_20260219_221600.pdf
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(temp_file_path)[1]
    new_filename = f"{user_id}_{timestamp}{ext}"
    new_path     = os.path.join(RESUME, new_filename)

    shutil.copy2(temp_file_path, new_path)  # คัดลอกไฟล์
    print(f"📁 บันทึกไฟล์: {new_path}")
    return new_path


# ══════════════════════════════════════════════════════════
# STEP 3: บันทึกผลการประเมินทั้งหมด
# ══════════════════════════════════════════════════════════

def save_to_db(user_id: str, result: dict, temp_file_path: str = "") -> bool:
    """
    บันทึกผลการประเมินและไฟล์ Resume ลง Database

    Args:
        user_id        : LINE user id
        result         : dict จาก process_resume()
        temp_file_path : path ไฟล์ PDF ชั่วคราว (จาก LINE)

    Returns:
        bool: True ถ้าบันทึกสำเร็จ

    Usage (จาก app_line.py):
        result = process_resume(file_path, job_id)
        save_to_db(user_id, result, file_path)
    """
    init_db()

    # บันทึกไฟล์ Resume ถาวร
    stored_path = ""
    if temp_file_path and os.path.exists(temp_file_path):
        stored_path = save_resume_file(user_id, temp_file_path)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
    INSERT INTO applicants (
        user_id,
        full_name,
        phone,
        email,
        university,
        job_id,
        job_title,
        score,
        passed,
        gpa,
        degree,
        gpa_pass,
        degree_pass,
        experience_years,
        experience_pass,
        skills_found,
        skills_missing,
        bonus_found,
        file_path,
        summary,
        recommendation,
        status,
        created_at
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", (
            user_id,
            result.get("full_name"),    
            result.get("phone"),       
            result.get("email"),       
            result.get("university"),
            # ตำแหน่งงาน
            result.get("job_id"),
            result.get("job_title"),

            # ผลการประเมิน
            result.get("score", 0),
            1 if result.get("passed") else 0,

            # การศึกษา
            result.get("gpa"),
            result.get("degree"),
            1 if result.get("gpa_pass") else 0,
            1 if result.get("degree_pass") else 0,

            # ประสบการณ์
            result.get("experience_years"),
            1 if result.get("experience_pass") else 0,

            # ทักษะ (เก็บเป็น JSON string)
            json.dumps(result.get("must_have_found", [])),
            json.dumps(result.get("must_have_missing", [])),
            json.dumps(result.get("nice_to_have_found", [])),

            # ไฟล์
            stored_path,

            # AI สรุป
            result.get("summary"),
            result.get("recommendation"),

            result.get("status", "confirmed"),  # <-- เพิ่มบรรทัดนี้

            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        print(f"✅ บันทึกสำเร็จ | {result.get('job_title')} | คะแนน: {result.get('score')}")
        return True

    except Exception as e:
        print(f"❌ บันทึกไม่สำเร็จ: {e}")
        return False


# ══════════════════════════════════════════════════════════
# STEP 4: ดึงข้อมูล (ใช้กับ Dashboard)
# ══════════════════════════════════════════════════════════

def get_all_applicants() -> list:
    """ดึงผู้สมัครทั้งหมด เรียงจากใหม่ → เก่า"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT * FROM applicants ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def get_passed_applicants() -> list:
    """ดึงเฉพาะคนที่ผ่านเกณฑ์ เรียงจากคะแนนสูง → ต่ำ"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT * FROM applicants WHERE passed = 1 ORDER BY score DESC"
    ).fetchall()
    conn.close()
    return rows


def get_applicants_by_job(job_id: str) -> list:
    """ดึงผู้สมัครตามตำแหน่งงาน"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT * FROM applicants WHERE job_id = ? ORDER BY score DESC",
        (job_id,)
    ).fetchall()
    conn.close()
    return rows
def get_waiting_resume_by_user(user_id: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT * FROM applicants
        WHERE user_id = ?
        AND status = 'waiting_confirm'
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id,)).fetchone()

    conn.close()
    return dict(row) if row else None
def update_resume_after_confirm(user_id: str, result: dict):
    init_db()
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        UPDATE applicants
        SET
            score = ?,
            passed = ?,
            gpa = ?,
            degree = ?,
            gpa_pass = ?,
            degree_pass = ?,
            experience_years = ?,
            experience_pass = ?,
            skills_found = ?,
            skills_missing = ?,
            bonus_found = ?,
            summary = ?,
            recommendation = ?,
            status = 'confirmed'
        WHERE user_id = ?
        AND status = 'waiting_confirm'
    """, (
        result.get("score", 0),
        1 if result.get("passed") else 0,
        result.get("gpa"),
        result.get("degree"),
        1 if result.get("gpa_pass") else 0,
        1 if result.get("degree_pass") else 0,
        result.get("experience_years"),
        1 if result.get("experience_pass") else 0,
        json.dumps(result.get("must_have_found", [])),
        json.dumps(result.get("must_have_missing", [])),
        json.dumps(result.get("nice_to_have_found", [])),
        result.get("summary"),
        result.get("recommendation"),
        user_id
    ))

    conn.commit()
    conn.close()

def get_summary_stats() -> dict:
    """สรุปสถิติภาพรวมสำหรับ Dashboard"""
    init_db()
    conn  = sqlite3.connect(DB_PATH)
    total  = conn.execute("SELECT COUNT(*) FROM applicants").fetchone()[0]
    passed = conn.execute("SELECT COUNT(*) FROM applicants WHERE passed = 1").fetchone()[0]
    avg    = conn.execute("SELECT AVG(score) FROM applicants").fetchone()[0]
    conn.close()
    return {
        "total":     total,
        "passed":    passed,
        "failed":    total - passed,
        "avg_score": round(avg, 1) if avg else 0
    }


# ══════════════════════════════════════════════════════════
# ทดสอบด้วย Resume จริง
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    from modules.resume_logic import process_resume  # รับผลจาก resume_logic

    print("กำลังวิเคราะห์ Resume...")
    result = process_resume("Resume_Manatsanan.pdf", "dev_backend")

    print("\nกำลังบันทึกลง Database...")
    save_to_db("test_user_001", result, "Resume_Manatsanan.pdf")

    # แสดงสถิติ
    stats = get_summary_stats()
    print(f"\n📊 สถิติภาพรวม:")
    print(f"  ผู้สมัครทั้งหมด : {stats['total']} คน")
    print(f"  ผ่านเกณฑ์      : {stats['passed']} คน")
    print(f"  ไม่ผ่าน        : {stats['failed']} คน")
    print(f"  คะแนนเฉลี่ย    : {stats['avg_score']}/100")