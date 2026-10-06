import streamlit as st
import fitz  # PyMuPDF (只用來把 PDF 模板轉成背景圖片)
import datetime
import os
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, PngImagePlugin
import base64

# ReportLab imports
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def embed_badge_metadata(template_path, output_path, voucher_code):
    """
    不修改圖片畫面，僅將 Voucher Code 內嵌進 PNG 檔案的 Metadata 中
    """
    if not os.path.exists(template_path):
        return None
        
    # 直接開啟原始徽章模板
    img = Image.open(template_path)
    
    # 建立 PNG 專屬的 Metadata (文字區塊)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("VoucherCode", voucher_code)
    metadata.add_text("Issuer", "Shisa Kanko-Shi Promotion Institute")
    metadata.add_text("CredentialType", "Digital Badge")
    
    # 儲存時帶入 pnginfo，將資料完美封裝進二進位檔案中
    img.save(output_path, "PNG", pnginfo=metadata)
    
    return output_path

# ==========================================
# Page Configuration
# ==========================================
st.set_page_config(
    page_title="Shisa Kanko-Shi Certificate Portal",
    page_icon="Icon1.png",
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
    
    reiwa_year = year - 2018
    
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
# 輔助函式：日文直書 (Vertical Writing)
# ==========================================
def draw_vertical_text(c, x, text, font_name, font_size, char_spacing=None, y_top=None, y_center=None):
    if char_spacing is None:
        char_spacing = font_size * 1.1
    
    num_chars = len(text)
    total_height = (num_chars - 1) * char_spacing
    
    if y_center is not None:
        start_y = y_center + (total_height / 2)
    elif y_top is not None:
        start_y = y_top
    else:
        start_y = 0
    
    c.setFont(font_name, font_size)
    for idx, char in enumerate(text):
        y_pos = start_y - (idx * char_spacing)
        char_width = c.stringWidth(char, font_name, font_size)
        c.drawString(x - (char_width / 2), y_pos, char)

# ==========================================
# PDF Certificate Generator Function (ReportLab)
# ==========================================
def generate_certificate_pdf(template_pdf_path, output_pdf_path, candidate_data):
    doc_fitz = fitz.open(template_pdf_path)
    page_fitz = doc_fitz[0]
    pix = page_fitz.get_pixmap(dpi=300)
    bg_image_path = "temp_cert_bg.png"
    pix.save(bg_image_path)
    
    rect = page_fitz.rect
    pdf_width, pdf_height = rect.width, rect.height
    doc_fitz.close()

    times_font_path = "times.ttf"
    yuji_font_path = "YujiSyuku-Regular.ttf"
    
    times_font_name = 'Times-Roman'
    if os.path.exists(times_font_path):
        pdfmetrics.registerFont(TTFont('CustomTimes', times_font_path))
        times_font_name = 'CustomTimes'
        
    yuji_font_name = 'Helvetica'
    if os.path.exists(yuji_font_path):
        pdfmetrics.registerFont(TTFont('YujiSyuku', yuji_font_path))
        yuji_font_name = 'YujiSyuku'

    first_name = str(candidate_data.get('EnglishFirstName', '')).strip()
    last_name = str(candidate_data.get('EnglishLastName', '')).strip()
    english_name = f"{first_name} {last_name}".strip()
    
    japanese_name = str(candidate_data.get('JapaneseName', '')).strip()
    exam_end_time = str(candidate_data.get('ExamEndTime', datetime.datetime.now().strftime("%Y-%m-%d"))).strip()
    voucher_code = str(candidate_data.get('VoucherCode', '')).strip()
    
    jp_date_str = convert_to_japanese_date(exam_end_time)

    c = canvas.Canvas(output_pdf_path, pagesize=(pdf_width, pdf_height))
    c.setTitle(f"Shisa Kanko-Shi Certificate - {voucher_code}")
    c.drawImage(bg_image_path, 0, 0, width=pdf_width, height=pdf_height)
    
    c.setFont(times_font_name, 30)
    c.drawCentredString(300, pdf_height - 250, english_name)
    
    draw_vertical_text(c, x=834, y_center=pdf_height - 320, text=japanese_name, font_name=yuji_font_name, font_size=36)
    
    c.setFont(times_font_name, 16)
    c.drawCentredString(180, pdf_height - 520, exam_end_time)
    
    draw_vertical_text(c, x=660, y_top=pdf_height - 350, text=jp_date_str, font_name=yuji_font_name, font_size=20, char_spacing=25)
    
    c.setFont(times_font_name, 11)
    c.drawCentredString(510, pdf_height - 660, voucher_code)
    
    c.save()
    
    if os.path.exists(bg_image_path):
        os.remove(bg_image_path)

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
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

img_base64 = get_base64_image("Icon1.png")

if img_base64:
    st.markdown(f"""
        <div style='text-align: center;'>
            <img src='data:image/png;base64,{img_base64}' width='120' style='vertical-align: middle; margin-right: 10px;'>
            <h1 style='display: inline-block; vertical-align: middle; margin: 0;'>Shisa Kanko-Shi Certificate Portal</h1>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("<h1 style='text-align: center;'>Shisa Kanko-Shi Certificate Portal</h1>", unsafe_allow_html=True)
st.write("Please enter your registered **Email Address** and **Voucher Code** below to retrieve and view your official certificate.")

with st.form("cert_lookup_form"):
    email_input = st.text_input("Registered Email Address:", placeholder="e.g., candidate@example.com").strip()
    voucher_input = st.text_input("Voucher Code:", placeholder="e.g., SK00001TEST").strip()
    submit_btn = st.form_submit_button("🔍 Look Up & Generate Certificate", use_container_width=True)

if submit_btn:
    if not email_input or not voucher_input:
        st.warning("⚠️ Please provide both your Email Address and Voucher Code.")
    else:
        matched_record = None
        exam_status = ""
        
        with st.spinner("Verifying credentials against examination database..."):
            try:
                db = get_sheets_connection()
                sheet = db.worksheet("Vouchers")
                records = sheet.get_all_records()
                
                for row in records:
                    v_code = str(row.get("VoucherCode", row.get("Voucher Code", ""))).strip()
                    c_email = str(row.get("AssignedEmail", row.get("Email", ""))).strip().replace("\n", "")
                    
                    if v_code.upper() == voucher_input.upper() and c_email.lower() == email_input.lower():
                        matched_record = row
                        break
                
                if matched_record:
                    exam_status = str(matched_record.get("ExamStatus", matched_record.get("exam_status", ""))).strip().lower()
            except Exception as e:
                st.error(f"An error occurred while connecting to the database: {e}")

        # 根據驗證狀態在畫面上渲染結果
        if not matched_record:
            st.error("❌ No matching record found. Please verify that both your Email Address and Voucher Code are correct.")
        elif exam_status == "dnf":
            st.error("Exam did not finish, please contact administrator")
        elif exam_status == "fail":
            st.error("❌ Record not found or invalid voucher code.")
        elif exam_status == "pass":
            st.success("✅ Credentials verified successfully!")
            
            # 1. 處理數位徽章下載
            badge_template = "CPCS-Badge.png"
            badge_output_filename = f"CPCS-Badge-{voucher_input}.png"
            
            if os.path.exists(badge_template):
                generated_badge_path = embed_badge_metadata(badge_template, badge_output_filename, voucher_input)
                if generated_badge_path and os.path.exists(generated_badge_path):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### 🛡️ Official Digital Badge")
                    
                    # 建立三欄排版，讓徽章置中在中間欄位
                    b_col1, b_col2, b_col3 = st.columns([1, 2, 1])
                    with b_col2:
                        st.image(generated_badge_path, width=250, caption="Personalized Official Badge")
                        
                        with open(generated_badge_path, "rb") as badge_file:
                            badge_bytes = badge_file.read()
                            
                        st.download_button(
                            label=f"📥 Download Digital Badge",
                            data=badge_bytes,
                            file_name=badge_output_filename,
                            mime="image/png",
                            use_container_width=True
                        )
                    
                    try:
                        os.remove(generated_badge_path)
                    except Exception:
                        pass
            else:
                st.warning(f"⚠️ Badge template file '{badge_template}' not found in repository root. Badge download skipped.")

            # 2. 處理 PDF 證書生成與預覽
            raw_date = str(matched_record.get("ExamEndTime", datetime.datetime.now().strftime("%Y-%m-%d"))).strip()
            formatted_exam_end_time = raw_date.split()[0] if raw_date else datetime.datetime.now().strftime("%Y-%m-%d")
            
            try:
                date_part = raw_date.split()[0]
                dt = datetime.datetime.strptime(date_part, "%Y-%m-%d")
                formatted_exam_end_time = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

            candidate_data = {
                "EnglishFirstName": str(matched_record.get("EnglishFirstName", matched_record.get("First Name", ""))).strip(),
                "EnglishLastName": str(matched_record.get("EnglishLastName", matched_record.get("Last Name", ""))).strip(),
                "JapaneseName": str(matched_record.get("JapaneseName", matched_record.get("Japanese Name", ""))).strip(),
                "ExamEndTime": formatted_exam_end_time,
                "VoucherCode": voucher_input
            }
            
            template_filename = "CSCP Certificate Template Final.pdf"
            output_filename = f"CPCS_Certificate_{voucher_input}.pdf"
            
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
                st.markdown("---")
        else:
            st.error("❌ Record not found or invalid voucher code.")
