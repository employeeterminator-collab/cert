import streamlit as st
import fitz  # PyMuPDF
import datetime
import os
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# Page Configuration
# ==========================================
st.set_page_config(
    page_title="Shisa Kanko-Shi Certificate Portal",
    page_icon="📜",
    layout="centered"
)

# ==========================================
# Google Sheets Connection Helper
# ==========================================
def get_sheets_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open("ShisaKanko_Exam_Database")

# ==========================================
# Date Conversion Helper (西元轉令和漢字日期)
# ==========================================
def convert_to_japanese_date(date_str):
    try:
        dt = datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except Exception:
        dt = datetime.datetime.now()
        
    year = dt.year
    month = dt.month
    day = dt.day
    
    reiwa_year = year - 2019
    
    kanji_numbers = {
        0: '〇', 1: '一', 2: '二', 3: '三', 4: '四',
        5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十',
        11: '十一', 12: '十二', 13: '十三', 14: '十四', 15: '十五',
        16: '十六', 17: '十七', 18: '十八', 19: '十九', 20: '二十',
        21: '二十一', 22: '二十二', 23: '二十三', 24: '二十四', 25: '二十五',
        26: '二十六', 27: '二十七', 28: '二十八', 29: '二十九', 30: '三十',
        31: '三十一'
    }
    
    def num_to_kanji(n):
        if n in kanji_numbers:
            return kanji_numbers[n]
        if n < 100:
            tens = n // 10
            ones = n % 10
            tens_str = '十' if tens == 1 else kanji_numbers[tens] + '十'
            ones_str = kanji_numbers[ones] if ones > 0 else ''
            return tens_str + ones_str
        return str(n)
    
    year_kanji = num_to_kanji(reiwa_year)
    month_kanji = num_to_kanji(month)
    day_kanji = num_to_kanji(day)
    
    return f"令和{year_kanji}年{month_kanji}月{day_kanji}日"

# ==========================================
# PDF Certificate Generator Function
# ==========================================
def generate_certificate_pdf(template_pdf_path, output_pdf_path, candidate_data):
    doc = fitz.open(template_pdf_path)
    page = doc[0]  # Single page certificate template
    
    first_name = str(candidate_data.get('EnglishFirstName', '')).strip()
    last_name = str(candidate_data.get('EnglishLastName', '')).strip()
    english_name = f"{first_name} {last_name}".strip()
    if not english_name or english_name == "":
        english_name = "Candidate Name"
        
    japanese_name = str(candidate_data.get('JapaneseName', '')).strip()
    if not japanese_name:
        japanese_name = "受講者 氏名"  # Fallback sample text if empty
        
    exam_end_time = str(candidate_data.get('ExamEndTime', datetime.datetime.now().strftime("%Y-%m-%d"))).strip()
    voucher_code = str(candidate_data.get('VoucherCode', '')).strip()
    
    jp_date_str = convert_to_japanese_date(exam_end_time)
    
    # Custom font file paths
    times_font_path = "times.ttf"          # Times New Roman for English
    yuji_font_path = "YujiSyuku.ttf"       # Yuji Syuku for Japanese[span_0](start_span)[span_0](end_span)
    
    has_times = os.path.exists(times_font_path)
    has_yuji = os.path.exists(yuji_font_path)

    # Register fonts to the page resource dictionary
    if has_times:
        page.insert_font(fontname="F1", fontfile=times_font_path)
    if has_yuji:
        page.insert_font(fontname="F2", fontfile=yuji_font_path)

    # 1. English Name (Using standard font or F1)
    if has_times:
        page.insert_text(fitz.Point(320, 480), english_name, fontsize=16, fontname="F1", color=(0, 0, 0))
    else:
        page.insert_text(fitz.Point(320, 480), english_name, fontsize=16, fontname="Times-Roman", color=(0, 0, 0))
    
    # 2. Japanese Name (Using Yuji Syuku F2)
    if has_yuji:
        page.insert_text(fitz.Point(320, 520), japanese_name, fontsize=16, fontname="F2", color=(0, 0, 0))
    else:
        page.insert_text(fitz.Point(320, 520), japanese_name, fontsize=16, color=(0, 0, 0))
    
    # 3. Exam Date
    if has_times:
        page.insert_text(fitz.Point(320, 560), exam_end_time, fontsize=12, fontname="F1", color=(0, 0, 0))
    else:
        page.insert_text(fitz.Point(320, 560), exam_end_time, fontsize=12, fontname="Times-Roman", color=(0, 0, 0))
    
    # 4. Japanese Kanji Date
    if has_yuji:
        page.insert_text(fitz.Point(320, 600), jp_date_str, fontsize=12, fontname="F2", color=(0, 0, 0))
    else:
        page.insert_text(fitz.Point(320, 600), jp_date_str, fontsize=12, color=(0, 0, 0))
    
    # 5. Voucher Code
    if has_times:
        page.insert_text(fitz.Point(450, 640), voucher_code, fontsize=11, fontname="F1", color=(0, 0, 0))
    else:
        page.insert_text(fitz.Point(450, 640), voucher_code, fontsize=11, fontname="Times-Roman", color=(0, 0, 0))
    
    doc.save(output_pdf_path)
    
    # Convert PDF first page to PNG image for on-screen preview
    preview_image_path = output_pdf_path.replace(".pdf", ".png")
    pix = page.get_pixmap(dpi=150)
    pix.save(preview_image_path)
    
    doc.close()
    return output_pdf_path, preview_image_path

# ==========================================
# Streamlit UI App Layout
# ==========================================
st.markdown("<h1 style='text-align: center;'>📜 Shisa Kanko-Shi Certificate Portal</h1>", unsafe_allow_html=True)
st.write("Please enter your registered **Email Address** and **Voucher Code** below to retrieve and view your official certificate.")

with st.form("cert_lookup_form"):
    email_input = st.text_input("Registered Email Address:", placeholder="e.g., candidate@example.com").strip()
    voucher_input = st.text_input("Voucher Code:", placeholder="e.g., SK00001TEST").strip()
    submit_btn = st.form_submit_button("🔍 Look Up & Generate Certificate", use_container_width=True)

if submit_btn:
    if not email_input or not voucher_input:
        st.warning("⚠️ Please provide both your Email Address and Voucher Code.")
    else:
        with st.spinner("Verifying credentials against examination database..."):
            try:
                db = get_sheets_connection()
                sheet = db.worksheet("Vouchers")
                records = sheet.get_all_records()
                
                matched_record = None
                for row in records:
                    v_code = str(row.get("VoucherCode", row.get("Voucher Code", ""))).strip()
                    c_email = str(row.get("AssignedEmail", row.get("Email", ""))).strip().replace("\n", "")
                    
                    if v_code.upper() == voucher_input.upper() and c_email.lower() == email_input.lower():
                        matched_record = row
                        break
                
                if matched_record:
                    # Show raw row keys so you can verify exact header names in Google Sheets
                    st.write("🔍 Raw Sheet Row Keys Found:", list(matched_record.keys()))
                    
                    candidate_data = {
                        "EnglishFirstName": str(matched_record.get("EnglishFirstName", matched_record.get("First Name", ""))).strip(),
                        "EnglishLastName": str(matched_record.get("EnglishLastName", matched_record.get("Last Name", ""))).strip(),
                        "JapaneseName": str(matched_record.get("JapaneseName", matched_record.get("Japanese Name", ""))).strip(),
                        "ExamEndTime": str(matched_record.get("ExamEndTime", matched_record.get("Exam End Time", datetime.datetime.now().strftime("%Y-%m-%d")))).strip(),
                        "VoucherCode": voucher_input
                    }
                    
                    st.write("📋 Mapped Candidate Data:", candidate_data)
                    st.success(f"✅ Credentials verified successfully!")
                    
                    template_filename = "CSCP Sample (20261005) TEMPLATE.pdf"
                    output_filename = f"Certificate_{voucher_input}.pdf"
                    
                    if not os.path.exists(template_filename):
                        st.error(f"❌ Certificate template file '{template_filename}' not found in your repository root.")
                    else:
                        generated_pdf_path, preview_image_path = generate_certificate_pdf(template_filename, output_filename, candidate_data)
                        
                        st.markdown("---")
                        st.markdown("### 🖥️ Certificate Preview")
                        st.image(preview_image_path, caption="Official Certificate Preview", use_column_width=True)
                        
                        with open(generated_pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            
                        st.markdown("---")
                        st.download_button(
                            label="📥 Download Official Certificate (PDF)",
                            data=pdf_bytes,
                            file_name=output_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.error("❌ No matching record found. Please verify that both your Email Address and Voucher Code are correct.")
            
            except Exception as e:
                st.error(f"An error occurred while connecting to the database: {e}")
