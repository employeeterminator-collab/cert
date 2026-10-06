import streamlit as st
import fitz  # PyMuPDF (只用來把 PDF 模板轉成背景圖片)
import datetime
import os
import gspread
from google.oauth2.service_account import Credentials

# ReportLab imports
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
# PDF Certificate Generator Function (ReportLab)
# ==========================================
def generate_certificate_pdf(template_pdf_path, output_pdf_path, candidate_data):
    # 1. 先用 PyMuPDF 把 PDF 模板的第一頁轉成暫存背景圖片
    doc_fitz = fitz.open(template_pdf_path)
    page_fitz = doc_fitz[0]
    pix = page_fitz.get_pixmap(dpi=300)
    bg_image_path = "temp_cert_bg.png"
    pix.save(bg_image_path)
    
    rect = page_fitz.rect
    pdf_width, pdf_height = rect.width, rect.height
    doc_fitz.close()

    # 2. 安全註冊自訂字型，若無則使用 ReportLab 內建標準字型
    times_font_path = "times.ttf"
    yuji_font_path = "YujiSyuku-Regular.ttf"
    
    times_font_name = 'Times-Roman'  # 預設內建
    if os.path.exists(times_font_path):
        pdfmetrics.registerFont(TTFont('CustomTimes', times_font_path))
        times_font_name = 'CustomTimes'
        
    yuji_font_name = 'Helvetica'      # 預設內建 Fallback
    if os.path.exists(yuji_font_path):
        pdfmetrics.registerFont(TTFont('YujiSyuku', yuji_font_path))
        yuji_font_name = 'YujiSyuku'

    # 3. 準備數據
    first_name = str(candidate_data.get('EnglishFirstName', '')).strip()
    last_name = str(candidate_data.get('EnglishLastName', '')).strip()
    english_name = f"{first_name} {last_name}".strip()
    
    japanese_name = str(candidate_data.get('JapaneseName', '')).strip()
    exam_end_time = str(candidate_data.get('ExamEndTime', datetime.datetime.now().strftime("%Y-%m-%d"))).strip()
    voucher_code = str(candidate_data.get('VoucherCode', '')).strip()
    
    jp_date_str = convert_to_japanese_date(exam_end_time)

    # 4. 使用 ReportLab 建立新 PDF 並繪製背景與文字
    c = canvas.Canvas(output_pdf_path, pagesize=(pdf_width, pdf_height))
    c.drawImage(bg_image_path, 0, 0, width=pdf_width, height=pdf_height)
    
    # English Name
    c.setFont(times_font_name, 16)
    c.drawString(320, pdf_height - 480, english_name)
    
    # Japanese Name (YujiSyuku)
    c.setFont(yuji_font_name, 16)
    c.drawString(320, pdf_height - 520, japanese_name)
    
    # Exam Date
    c.setFont(times_font_name, 12)
    c.drawString(320, pdf_height - 560, exam_end_time)
    
    # Japanese Kanji Date (YujiSyuku)
    c.setFont(yuji_font_name, 12)
    c.drawString(320, pdf_height - 600, jp_date_str)
    
    # Voucher Code
    c.setFont(times_font_name, 11)
    c.drawString(450, pdf_height - 640, voucher_code)
    
    c.save()
    
    # 5. 清理暫存背景圖
    if os.path.exists(bg_image_path):
        os.remove(bg_image_path)

    # 6. 轉成 PNG 預覽
    doc_out = fitz.open(output_pdf_path)
    page_out = doc_out[0]
    preview_pix = page_out.get_pixmap(dpi=150)
    preview_image_path = output_pdf_path.replace(".pdf", ".png")
    preview_pix.save(preview_image_path)
    doc_out.close()
    
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
                    candidate_data = {
                        "EnglishFirstName": str(matched_record.get("EnglishFirstName", matched_record.get("First Name", ""))).strip(),
                        "EnglishLastName": str(matched_record.get("EnglishLastName", matched_record.get("Last Name", ""))).strip(),
                        "JapaneseName": str(matched_record.get("JapaneseName", matched_record.get("Japanese Name", ""))).strip(),
                        "ExamEndTime": str(matched_record.get("ExamEndTime", matched_record.get("Exam End Time", datetime.datetime.now().strftime("%Y-%m-%d")))).strip(),
                        "VoucherCode": voucher_input
                    }
                    
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
