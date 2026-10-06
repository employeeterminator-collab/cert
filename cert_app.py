import streamlit as st
import fitz  # PyMuPDF
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import io
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Certificate Generator Portal",
    page_icon="📜",
    layout="centered"
)

# --- Configuration Constants ---
TEMPLATE_PDF = "certificate_template.pdf"
FONT_PATH = "YujiSyuku-Regular.ttf"  # Custom font file
SHEET_NAME = "Certificate_Database"  # Update with your Google Sheet name

# --- Authentication Setup ---
def check_authentication():
    """Handles simple email and voucher code authentication."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.subheader("🔒 Portal Access Authentication")
        email = st.text_input("Email Address")
        voucher = st.text_input("Voucher / Access Code", type="password")
        
        if st.button("Login"):
            # Simple validation logic (modify rules as needed)
            if email and voucher:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email
                st.rerun()
            else:
                st.error("Please provide both an email and an access code.")
        return False
    return True

# --- Google Sheets Connection ---
def get_google_sheet_data():
    """Fetches candidate records from Google Sheets."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Assumes Streamlit secrets are configured for service account credentials
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return []

# --- PDF Generation Engine ---
def generate_certificate(name, issue_date, course_title):
    """Inserts candidate details into the PDF template using PyMuPDF and custom fonts."""
    try:
        doc = fitz.open(TEMPLATE_PDF)
        page = doc[0]  # Select the first page of the template

        # Register custom font for multi-language support (English / Japanese)
        # PyMuPDF allows inserting fonts via registerFont
        font_name = "YujiSyuku"
        page.insert_font(fontname=font_name, fontfile=FONT_PATH)

        # Define coordinates and styling for text placement (Adjust X, Y points as needed)
        # Example coordinates:
        
        # 1. Candidate Name Insertion
        page.insert_text(
            point=(300, 350), 
            text=name, 
            fontsize=36, 
            fontname=font_name, 
            color=(0.1, 0.1, 0.1)
        )

        # 2. Course Title Insertion
        page.insert_text(
            point=(300, 450), 
            text=course_title, 
            fontsize=20, 
            fontname=font_name, 
            color=(0.2, 0.2, 0.2)
        )

        # 3. Issue Date Insertion
        page.insert_text(
            point=(200, 550), 
            text=issue_date, 
            fontsize=14, 
            fontname=font_name, 
            color=(0.3, 0.3, 0.3)
        )

        # Render PDF page to an image for on-screen preview
        pix = page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        # Save output bytes for download
        pdf_bytes = doc.write()
        doc.close()
        
        return pdf_bytes, img

    except Exception as e:
        st.error(f"Failed to generate certificate: {e}")
        return None, None

# --- Main Application Workflow ---
def main():
    st.title("📜 Automated Certificate Generator")
    st.markdown("Generate and preview custom certificates seamlessly from your database records.")

    # Run Authentication Check
    if not check_authentication():
        return

    st.sidebar.success(f"Logged in as: {st.session_state.get('user_email')}")
    if st.sidebar.button("Log Out"):
        st.session_state["authenticated"] = False
        st.rerun()

    st.divider()

    # Fetch data source options
    records = get_google_sheet_data()
    
    if records:
        # Create a selection mapping based on recipient names or identifiers
        recipient_names = [record.get("Name", "Unknown") for record in records]
        selected_name = st.selectbox("Select Candidate", recipient_names)

        # Retrieve the specific record data
        selected_record = next((r for r in records if r.get("Name") == selected_name), None)

        if selected_record:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Record Details")
                st.write(f"**Name:** {selected_record.get('Name')}")
                st.write(f"**Course:** {selected_record.get('Course', 'Standard Certification')}")
                st.write(f"**Date:** {selected_record.get('Date', '2026-10-05')}")

            # Trigger generation inputs
            name_input = selected_record.get("Name")
            course_input = selected_record.get("Course", "Professional Training Course")
            date_input = selected_record.get("Date", "2026-10-05")

            if st.button("Generate Certificate Preview"):
                with st.spinner("Rendering certificate layout..."):
                    pdf_bytes, preview_image = generate_certificate(name_input, date_input, course_input)
                    
                    if pdf_bytes and preview_image:
                        st.session_state["pdf_bytes"] = pdf_bytes
                        st.session_state["preview_image"] = preview_image
                        st.success("Certificate generated successfully!")

            # Display Preview and Download options if available in session state
            if "pdf_bytes" in st.session_state:
                st.image(st.session_state["preview_image"], caption="Certificate Preview", use_container_width=True)
                
                st.download_button(
                    label="📥 Download Official Certificate (PDF)",
                    data=st.session_state["pdf_bytes"],
                    file_name=f"Certificate_{name_input.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("No records found or unable to connect to Google Sheets. Please ensure your configuration and credentials are correct.")

if __name__ == "__main__":
    main()
