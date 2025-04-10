import os
import sys
import re
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import pytesseract

# Optional: Set Tesseract executable path if it's not in your PATH:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Optional: For pdf2image, set the poppler path if needed (example for Windows or custom setups):
# poppler_path = r"C:\path\to\poppler-xx\bin"
poppler_path = None  # Set this to your poppler bin path if necessary


##############################
# Function for PDF files (existing functionality)
##############################

def extract_invoice_number_from_pdf(pdf_path):
    """
    Converts the PDF to image(s) and uses OCR to extract text.
    Searches for the invoice number in the format "RE-XXXX-XX" where X is a digit.
    Returns the first found invoice number or None if not found.
    """
    invoice_number = None
    # Regex pattern matching "RE-" then 4 digits, a hyphen, and 2 digits.
    invoice_regex = re.compile(r"RE-\d{4}-\d{2}")

    try:
        # Convert the PDF file pages to images; assuming each PDF is a scanned document.
        if poppler_path:
            pages = convert_from_path(pdf_path, poppler_path=poppler_path)
        else:
            pages = convert_from_path(pdf_path)

        # Iterate over pages in the PDF (in case the invoice number might appear on any page)
        for page in pages:
            text = pytesseract.image_to_string(page)
            match = invoice_regex.search(text)
            if match:
                invoice_number = match.group(0)
                break
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
    return invoice_number


def merge_pdfs(pdf_paths, output_pdf_path):
    """
    Merges multiple PDF files into a single PDF file.
    """
    pdf_writer = PdfWriter()
    for path in pdf_paths:
        try:
            pdf_reader = PdfReader(path)
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
        except Exception as e:
            print(f"Error reading {path}: {e}")
    try:
        with open(output_pdf_path, 'wb') as out_pdf:
            pdf_writer.write(out_pdf)
        print(f"Created merged PDF: {output_pdf_path}")
    except Exception as e:
        print(f"Error writing PDF {output_pdf_path}: {e}")


def process_pdf_folder(folder_path):
    """
    Processes all PDF files in the provided folder.
    Groups them by invoice number (format "RE-XXXX-XX") and merges those
    with at least two files, logging unpaired files.
    """
    invoice_groups = {}
    unprocessed_files = []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.lower().endswith('.pdf'):
            invoice_num = extract_invoice_number_from_pdf(file_path)
            if invoice_num:
                invoice_groups.setdefault(invoice_num, []).append(file_path)
            else:
                unprocessed_files.append(filename)
        else:
            continue

    output_folder = os.path.join(folder_path, "output_pdfs")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    unpaired_files = []
    for invoice_num, pdf_list in invoice_groups.items():
        if len(pdf_list) >= 2:
            output_pdf_filename = f"Invoice_{invoice_num}.pdf"
            output_pdf_path = os.path.join(output_folder, output_pdf_filename)
            merge_pdfs(pdf_list, output_pdf_path)
        else:
            for pdf in pdf_list:
                unpaired_files.append((invoice_num, os.path.basename(pdf)))

    log_path = os.path.join(folder_path, "log.txt")
    with open(log_path, "w") as log_file:
        log_file.write("Files without an identifiable invoice number or not paired:\n")
        for fname in unprocessed_files:
            log_file.write(f"No invoice found: {fname}\n")
        for invoice_num, fname in unpaired_files:
            log_file.write(f"Unpaired for invoice {invoice_num}: {fname}\n")
    print(f"Log file created at {log_path}")


##############################
# New Function: Process JPEG files
##############################

def convert_jpegs_to_pdf(folder_path):
    """
    Processes all JPEG/JPG files in the given folder.
    Uses OCR to extract text, searches for a date on the receipt/invoice,
    and converts the image to a PDF named by the detected date.
    If no date is found, the original filename (without extension) is used.
    The PDFs are stored in a subfolder called 'jpeg_output_pdfs'.
    """
    # Look for files ending in .jpg or .jpeg
    jpeg_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))]
    output_folder = os.path.join(folder_path, "jpeg_output_pdfs")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Regex pattern to match common date formats e.g. 19.11.2024, 19-11-2024 or 19/11/2024.
    date_regex = re.compile(r'\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b')

    for file in jpeg_files:
        file_path = os.path.join(folder_path, file)
        try:
            im = Image.open(file_path)
            # Use OCR to extract text from the JPEG
            text = pytesseract.image_to_string(im)
            # For debugging purposes, you can print the OCR result:
            # print(f"OCR for {file}:\n{text}")

            date_match = date_regex.search(text)
            if date_match:
                date_str = date_match.group(0)
                base_name = date_str
            else:
                base_name = os.path.splitext(file)[0]
                print(f"No date found in {file}, using file name as base")

            output_filename = f"{base_name}.pdf"
            output_path = os.path.join(output_folder, output_filename)
            counter = 1
            # Avoid filename collisions by appending a counter if needed.
            while os.path.exists(output_path):
                output_filename = f"{base_name}_{counter}.pdf"
                output_path = os.path.join(output_folder, output_filename)
                counter += 1

            # Convert the JPEG to PDF; convert to RGB if necessary.
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.save(output_path, "PDF", resolution=100.0)
            print(f"Converted {file} to {output_filename}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")


##############################
# Main section: Call the desired functions
##############################

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <folder_path>")
    else:
        folder_path = sys.argv[1]

        # Process PDF files (invoices and proof of payments)
        process_pdf_folder(folder_path)

        # Process JPEG files and convert them to PDFs named by receipt/invoice date
        convert_jpegs_to_pdf(folder_path)
