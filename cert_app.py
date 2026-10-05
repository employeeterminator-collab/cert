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
    page_title="Shisa Kanko-Shi Certificate Generator",
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
    # Uses Streamlit Secrets for secure credential management
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # Open your exam database spreadsheet
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
    
    # Extract fields based on requested column mappings
    first_name = str(candidate_data.get('EnglishFirstName', '')).strip()
    last_name = str(candidate_data.get('EnglishLastName', '')).strip()
    english_name = f"{first_name} {last_name}".strip()
    
    japanese_name = str(candidate_data.get('JapaneseName', '')).strip()
    exam_end_time = str(candidate_data.get('ExamEndTime', datetime.datetime.now().strftime("%Y-%m-%d"))).strip()
    voucher_code = str(candidate_data.get('VoucherCode', '')).strip()
    
    jp_date_str = convert_to_japanese_date(exam_end_time)
    
    # ==========================================
    # Text Insertion Coordinates on Template PDF
    # (Adjust coordinates X, Y to match your template layout precisely)
    # ==========================================
    
    # 1. English Name (e.g., John Doe)
    page.insert_text(fitz.Point(250, 450), english_name, fontsize=14, fontname="Helvetica")
    
    # 2. Japanese Name (e.g., ジョン・ドウ)
    page.insert_text(fitz.Point(250, 480), japanese_name, fontsize=14)
    
    # 3. Exam Date (e.g., 2026-10-05)
    page.insert_text(fitz.Point(250, 510), exam_end_time, fontsize=12, fontname="Helvetica")
    
    # 4. Japanese Date Kanji (e.g., 令和八年十月五日)
    page.insert_text(fitz.Point(250, 540), jp_date_str, fontsize=12)
    
    # 5. Voucher Code / Certificate Number (e.g., SK00001TEST)
    page.insert_text(fitz.Point(450, 570), voucher_code, fontsize=11, fontname="Helvetica")
    
    doc.save(output_pdf_path)
    doc.close()
    return output_pdf_path

# ==========================================
# Streamlit UI App Layout
# ==========================================
st.markdown("<h1 style='text-align: center;'>📜 Shisa Kanko-Shi Certificate Portal</h1>", unsafe_allow_html=True)
st.write("Enter your **Voucher Code** below to verify your passing status and download your official certificate of designation.")

voucher_input = st.text_input("Voucher Code:", placeholder="e.g., SK00001TEST").strip()

if st.button("🔍 Look Up Certificate", type="primary", use_container_width=True):
    if not voucher_input:
        st.warning("⚠️ Please enter a valid voucher code.")
    else:
        with st.spinner("Connecting to examination database..."):
            try:
                db = get_sheets_connection()
                sheet = db.worksheet("Vouchers")
                records = sheet.get_all_records()
                
                # Search for matching voucher code in records
                matched_record = None
                for row in records:
                    # Check common voucher key names in Google Sheet
                    v_code = str(row.get("VoucherCode", row.get("Voucher Code", ""))).strip()
                    if v_code.upper() == voucher_input.upper():
                        matched_record = row
                        break
                
                if matched_record:
                    # Check if candidate passed
                    status = str(matched_record.get("Status", matched_record.get("ExamStatus", ""))).strip()
                    
                    # Map columns based on your schema instructions:
                    # Col6: EnglishFirstName, Col7: EnglishLastName, Col12: ExamEndTime, JapaneseName, VoucherCode
                    headers = sheet.row_values(1)
                    row_vals = sheet.row_values(sheet.find(voucher_input).row)
                    
                    # Helper to safely get values by header name or index position
                    def get_col_val(col_name_keyword, col_index_1_based):
                        for idx, h in enumerate(headers):
                            if col_name_keyword.lower() in h.lower():
                                if idx < len(row_vals):
                                    return row_vals[idx]
                        if col_index_1_based - 1 < len(row_vals):
                            return row_vals[col_index_1_based - 1]
                        return ""

                    candidate_data = {
                        "EnglishFirstName": get_col_val("FirstName", 6),
                        "EnglishLastName": get_col_val("LastName", 7),
                        "JapaneseName": get_col_val("JapaneseName", 9), # Adjust index if needed
                        "ExamEndTime": get_col_val("EndTime", 12),
                        "VoucherCode": voucher_input
                    }
                    
                    st.success(f"✅ Verified record found for **{candidate_data['EnglishFirstName']} {candidate_data['EnglishLastName']}**!")
                    
                    # Generate PDF on the fly
                    template_filename = "CSCP Sample (20261005) TEMPLATE.pdf"
                    output_filename = f"Certificate_{voucher_input}.pdf"
                    
                    if not os.path.exists(template_filename):
                        st.error(f"❌ Certificate template file '{template_filename}' not found in the app directory. Please upload it to your project root.")
                    else:
                        generated_pdf_path = generate_certificate_pdf(template_filename, output_filename, candidate_data)
                        
                        with open(generated_pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            
                        st.markdown("---")
                        st.markdown("### 🎉 Your Certificate is Ready!")
                        st.download_button(
                            label="📥 Download Official Certificate (PDF)",
                            data=pdf_bytes,
                            file_name=output_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.error("❌ No matching record found for this voucher code. Please check your code and try again.")
            
            except Exception as e:
                st.error(f"An error occurred while connecting to the database: {e}")
