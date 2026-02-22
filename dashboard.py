import streamlit as st
import sqlite3
import pandas as pd
import os

# ตั้งค่าหน้าจอ
st.set_page_config(page_title="HR Smart Resume Dashboard", layout="wide", page_icon="📊")

# ฟังก์ชันดึงข้อมูลจาก DB
def get_data():
    conn = sqlite3.connect("resume_bot.db")
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

df = get_data()

# --- ส่วนหัวและสถิติ ---
st.markdown("<h1 style='text-align: center;'>📊 Smart Resume Analyst - HR Dashboard</h1>", unsafe_allow_html=True)

if not df.empty:
    # แก้ไขส่วน Metrics ที่หายไปให้กลับมาโชว์สวยๆ
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

# --- ส่วนเนื้อหาหลัก ---
col_table, col_detail = st.columns([1.8, 1.2])

with col_table:
    st.subheader("📋 รายชื่อผู้สมัคร")
    # ช่องค้นหา
    search_term = st.text_input("🔍 ค้นหาชื่อ หรือ ตำแหน่งงาน", "")
    
    # Filter ข้อมูล
    filtered_df = df[
        df['full_name'].str.contains(search_term, case=False, na=False) | 
        df['job_title'].str.contains(search_term, case=False, na=False)
    ]

    # แสดงตารางแบบ Interactive
    event = st.dataframe(
        filtered_df[['id', 'full_name', 'job_title', 'score', 'status']],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

with col_detail:
    st.subheader("🔍 รายละเอียดเชิงลึก")
    
    if len(event.selection.rows) > 0:
        # ดึงข้อมูลจากแถวที่ HR คลิกเลือก
        selected_idx = event.selection.rows[0]
        row = filtered_df.iloc[selected_idx]
        
        # แสดงข้อมูลแบบสวยงาม
        st.markdown(f"### **คุณ {row['full_name']}**")
        
        # ใช้ Column ย่อยในส่วนรายละเอียด
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

        # ปุ่มดาวน์โหลดไฟล์ PDF
        path = row['file_path']
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                st.download_button(
                    label="📥 ดาวน์โหลด Resume (PDF)",
                    data=f,
                    file_name=os.path.basename(path),
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
        else:
            st.error("ไม่พบไฟล์ PDF ในระบบ")
    else:
        st.info("👈 คลิกเลือกรายชื่อในตารางเพื่อดูข้อมูลและดาวน์โหลดไฟล์")

# --- ส่วนตารางด้านล่าง ---
st.divider()
st.subheader("🏆 ผู้สมัครคะแนนสูงสุด 5 อันดับแรก")
top5 = df.sort_values(by='score', ascending=False).head(5)
st.table(top5[['full_name', 'job_title', 'score', 'university']])