import streamlit as st
import sqlite3
import pandas as pd
import os
import json

from app.database import init_db

# 🌟 1. ตั้งค่าหน้าจอ (ต้องอยู่บนสุดเสมอ)
st.set_page_config(page_title="HR Smart Resume Dashboard", layout="wide", page_icon="📊")

DB_PATH = "resume_bot.db"

init_db()

# ─────────────────────────────────────────────
# 🌟 2. รวมฟังก์ชันทั้งหมด
# ─────────────────────────────────────────────
def get_all_jobs():
    """ดึงรายชื่อตำแหน่งงานทั้งหมดจาก jobs.json"""
    try:
        with open("jobs.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("ไม่พบไฟล์ jobs.json")
        return {}

def get_job_statuses():
    """ดึงสถานะเปิด-ปิดตำแหน่งจาก DB"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT job_id, is_active FROM jobs_status").fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def update_job_status(job_id: str, is_active: int):
    """อัปเดตสถานะลง DB"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO jobs_status (job_id, is_active) 
        VALUES (?, ?)
        ON CONFLICT(job_id) DO UPDATE SET is_active=excluded.is_active
    """, (job_id, is_active))
    conn.commit()
    conn.close()

def get_data():
    """ดึงข้อมูลผู้สมัครจาก DB"""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        id, full_name, phone, email, university, 
        job_title, score, status, summary, file_path,
        gpa, degree, experience_years, recommendation
    FROM applicants
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def delete_applicant(applicant_id):
    """ลบข้อมูลผู้สมัครออกจาก DB"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applicants WHERE id = ?", (int(applicant_id),))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# 🌟 3. ส่วนแถบเมนูด้านข้าง (Sidebar) - สำหรับเปิด/ปิดงาน
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ จัดการตำแหน่งงาน")
    st.caption("เปิด/ปิด รับสมัครได้ที่นี่")
    
    jobs = get_all_jobs()
    statuses = get_job_statuses()

    if jobs:
        for job_id, job_info in jobs.items():
            current_status = statuses.get(job_id, 1) 
            
            # ปุ่ม Toggle
            is_active_bool = st.toggle(
                f"{job_info['title']}", 
                value=bool(current_status), 
                key=job_id
            )
            
            new_status = 1 if is_active_bool else 0
            if new_status != current_status:
                update_job_status(job_id, new_status)
                st.toast(f"อัปเดตสถานะ {job_info['title']} เรียบร้อย! ✅")

# ─────────────────────────────────────────────
# 🌟 4. ส่วนเนื้อหาหลัก (Main Dashboard)
# ─────────────────────────────────────────────
st.markdown("<h1 style='text-align: center;'>📊 Smart Resume Analyst - HR Dashboard</h1>", unsafe_allow_html=True)

df = get_data()

if not df.empty:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.info("👥 ผู้สมัครทั้งหมด")
        st.subheader(f"{len(df)} คน")
    with m2:
        st.success("✅ ส่งให้ HR แล้ว")
        st.subheader(f"{len(df[df['status'] == 'confirmed'])} คน")
    with m3:
        st.warning("⏳ รอการยืนยัน")
        st.subheader(f"{len(df[df['status'] == 'waiting_confirm'])} คน")
    with m4:
        st.error("📈 คะแนนเฉลี่ย")
        st.subheader(f"{round(df['score'].mean(), 1)} / 100")

st.divider()

col_table, col_detail = st.columns([1.8, 1.2])

with col_table:
    st.subheader("📋 รายชื่อผู้สมัคร")
    
    f1, f2, f3 = st.columns([2, 1.5, 1.5])
    with f1:
        search_term = st.text_input("🔍 ค้นหาชื่อ/ตำแหน่ง", "")
    with f2:
        status_filter = st.selectbox("📌 สถานะ", ["ทั้งหมด", "✅ confirmed", "⏳ waiting_confirm", "❌ rejected", "⚠️ ข้อมูลไม่สมบูรณ์"])
    with f3:
        score_filter = st.selectbox("⭐ คะแนน AI", ["ทั้งหมด", "ผ่านเกณฑ์ (50+)", "คะแนนสูง (80+)"])

    # กรองข้อมูล
    if search_term.strip() == "":
        filtered_df = df.copy()
    else:
        filtered_df = df[
            df['full_name'].fillna("").str.contains(search_term, case=False) | 
            df['job_title'].fillna("").str.contains(search_term, case=False)
        ].copy()

    if status_filter == "✅ confirmed":
        filtered_df = filtered_df[filtered_df['status'] == 'confirmed']
    elif status_filter == "⏳ waiting_confirm":
        filtered_df = filtered_df[filtered_df['status'] == 'waiting_confirm']
    elif status_filter == "❌ rejected":
        filtered_df = filtered_df[filtered_df['status'] == 'rejected']
    elif status_filter == "⚠️ ข้อมูลไม่สมบูรณ์":
        filtered_df = filtered_df[filtered_df['status'].isna() | (filtered_df['full_name'].isna())]

    filtered_df['numeric_score'] = pd.to_numeric(filtered_df['score'], errors='coerce').fillna(0)
    
    if score_filter == "ผ่านเกณฑ์ (50+)":
        filtered_df = filtered_df[filtered_df['numeric_score'] >= 50]
    elif score_filter == "คะแนนสูง (80+)":
        filtered_df = filtered_df[filtered_df['numeric_score'] >= 80]

    # เลือกเฉพาะคอลัมน์ที่จะโชว์
    display_df = filtered_df[['id', 'full_name', 'job_title', 'score', 'status']]

    # แสดงตาราง
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

with col_detail:
    st.subheader("🔍 รายละเอียดเชิงลึก")
    
    if len(event.selection.rows) > 0:
        selected_idx = event.selection.rows[0]
        row = filtered_df.iloc[selected_idx]
        
        st.markdown(f"### **คุณ {row['full_name']}**")
        
        d1, d2 = st.columns(2)
        with d1:
            st.write(f"📞 **เบอร์:** {row['phone']}")
            st.write(f"🎓 **มหาลัย:** {row['university']}")
        with d2:
            st.write(f"📧 **อีเมล:** {row['email']}")
            st.write(f"📜 **วุฒิ:** {row['degree']}")

        st.markdown(f"**📊 คะแนนวิเคราะห์:** `{row['score']}/100`")
        
        st.markdown("---")
        st.markdown("**📝 สรุปความสามารถ:**")
        st.caption(row['summary'])
        
        st.markdown("**💡 AI Recommendation:**")
        st.success(row['recommendation'])

        # ปุ่มดาวน์โหลด
        path = row['file_path']
        if path and pd.notna(path) and os.path.exists(path):
            with open(path, "rb") as f:
                st.download_button(
                    label="📥 ดาวน์โหลด Resume (PDF)",
                    data=f,
                    file_name=os.path.basename(path),
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ ไม่พบไฟล์ PDF ในระบบ")

        st.markdown("---")
        
        # ปุ่มลบ
        if st.button("🗑️ ลบข้อมูลผู้สมัครรายนี้", type="primary", use_container_width=True):
            delete_applicant(row['id'])
            if path and pd.notna(path) and os.path.exists(path):
                try: os.remove(path)
                except: pass
            st.success("✅ ลบข้อมูลสำเร็จ! กำลังรีเฟรช...")
            st.rerun()
    else:
        st.info("👈 คลิกเลือกรายชื่อในตารางเพื่อดูข้อมูล ดาวน์โหลดไฟล์ หรือลบข้อมูล")

st.divider()
st.subheader("🏆 ผู้สมัครคะแนนสูงสุด 5 อันดับแรก")
top5 = df.sort_values(by='score', ascending=False).head(5)
st.table(top5[['full_name', 'job_title', 'score', 'university']])