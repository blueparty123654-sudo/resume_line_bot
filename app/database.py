"""
database.py
===========
รับผิดชอบ: บันทึกและดึงข้อมูลผู้สมัครจาก SQLite Database
"""

import sqlite3
import shutil
import os
import json
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DB_PATH = "resume_bot.db"
RESUME_FOLDER = "resumes/"

# ─────────────────────────────────────────────
# STEP 1: สร้าง Table
# ─────────────────────────────────────────────
def init_db():
    os.makedirs(RESUME_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # 1. ตารางเก็บข้อมูลผู้สมัคร
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, full_name TEXT, phone TEXT, email TEXT,
            university TEXT, job_id TEXT, job_title TEXT,
            score REAL, passed INTEGER, gpa REAL, degree TEXT,
            gpa_pass INTEGER, degree_pass INTEGER,
            experience_years INTEGER, experience_pass INTEGER,
            skills_found TEXT, skills_missing TEXT, bonus_found TEXT,
            file_path TEXT, summary TEXT, recommendation TEXT,
            status TEXT, created_at TEXT
        )
    """)

    # 2. ตารางจัดการสิทธิ์ HR
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            line_id TEXT PRIMARY KEY,
            role TEXT DEFAULT 'user'
        )
    """)

    # 3. ตารางเปิด-ปิดตำแหน่งงาน
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs_status (
            job_id TEXT PRIMARY KEY,
            is_active INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# STEP 2: บันทึกไฟล์ Resume ถาวร
# ─────────────────────────────────────────────
def save_resume_file(user_id: str, temp_file_path: str) -> str:
    os.makedirs(RESUME_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(temp_file_path)[1]
    new_filename = f"{user_id}_{timestamp}{ext}"
    new_path = os.path.join(RESUME_FOLDER, new_filename)

    shutil.copy2(temp_file_path, new_path)
    print(f"📁 บันทึกไฟล์: {new_path}")
    return new_path

# ─────────────────────────────────────────────
# STEP 3: บันทึกและอัปเดตผลการประเมิน
# ─────────────────────────────────────────────
def save_to_db(user_id: str, result: dict, temp_file_path: str = "") -> bool:
    init_db()
    stored_path = ""
    if temp_file_path and os.path.exists(temp_file_path):
        stored_path = save_resume_file(user_id, temp_file_path)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO applicants (
                user_id, full_name, phone, email, university, job_id, job_title,
                score, passed, gpa, degree, gpa_pass, degree_pass,
                experience_years, experience_pass, skills_found, skills_missing, bonus_found,
                file_path, summary, recommendation, status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            user_id, result.get("full_name"), result.get("phone"), result.get("email"), result.get("university"),
            result.get("job_id"), result.get("job_title"), result.get("score", 0), 1 if result.get("passed") else 0,
            result.get("gpa"), result.get("degree"), 1 if result.get("gpa_pass") else 0, 1 if result.get("degree_pass") else 0,
            result.get("experience_years"), 1 if result.get("experience_pass") else 0,
            json.dumps(result.get("must_have_found", [])), json.dumps(result.get("must_have_missing", [])), json.dumps(result.get("nice_to_have_found", [])),
            stored_path, result.get("summary"), result.get("recommendation"), result.get("status", "confirmed"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        print(f"✅ บันทึกสำเร็จ | {result.get('job_title')} | คะแนน: {result.get('score')}")
        return True
    except Exception as e:
        print(f"❌ บันทึกไม่สำเร็จ: {e}")
        return False

def update_resume_after_confirm(user_id: str, result: dict):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        UPDATE applicants
        SET score = ?, passed = ?, gpa = ?, degree = ?, gpa_pass = ?, degree_pass = ?,
            experience_years = ?, experience_pass = ?, skills_found = ?, skills_missing = ?,
            bonus_found = ?, summary = ?, recommendation = ?, status = 'confirmed'
        WHERE user_id = ? AND status = 'waiting_confirm'
    """, (
        result.get("score", 0), 1 if result.get("passed") else 0, result.get("gpa"), result.get("degree"),
        1 if result.get("gpa_pass") else 0, 1 if result.get("degree_pass") else 0, result.get("experience_years"),
        1 if result.get("experience_pass") else 0, json.dumps(result.get("must_have_found", [])),
        json.dumps(result.get("must_have_missing", [])), json.dumps(result.get("nice_to_have_found", [])),
        result.get("summary"), result.get("recommendation"), user_id
    ))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# STEP 4: ดึงข้อมูล (ใช้กับ Dashboard และการ Confirm)
# ─────────────────────────────────────────────
def get_all_applicants() -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM applicants ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows

def get_passed_applicants() -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM applicants WHERE passed = 1 ORDER BY score DESC").fetchall()
    conn.close()
    return rows

def get_applicants_by_job(job_id: str) -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM applicants WHERE job_id = ? ORDER BY score DESC", (job_id,)).fetchall()
    conn.close()
    return rows

def get_waiting_resume_by_user(user_id: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT * FROM applicants WHERE user_id = ? AND status = 'waiting_confirm' ORDER BY created_at DESC LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_summary_stats() -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM applicants").fetchone()[0]
    passed = conn.execute("SELECT COUNT(*) FROM applicants WHERE passed = 1").fetchone()[0]
    avg = conn.execute("SELECT AVG(score) FROM applicants").fetchone()[0]
    conn.close()
    return {
        "total": total, "passed": passed, "failed": total - passed,
        "avg_score": round(avg, 1) if avg else 0
    }