from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pytesseract
import os
import re

app = FastAPI()

# Allow CORS for specific origins
origins = [
    "http://localhost:4200",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

app.mount("/static", StaticFiles(directory="static"), name="static")

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Directory to store uploaded files
UPLOAD_DIRECTORY = "static/temp_receipt"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True) 


def extract_text_from_image(image_path):
    """
    Extracts text from the image using pytesseract.
    """
    try:
        text = pytesseract.image_to_string(image_path)
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from image: {e}")


def save_uploaded_file(file: UploadFile):
    """
    Save the uploaded file to the server.
    """
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        if os.path.getsize(file_path) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        return file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")


def extract_receipt_data(text):
    """
    Extracts receipt-specific fields such as Vendor Name, Receipt Number, Date, Payment Amount, etc.
    from the OCR text. Designed specifically for payment receipts.
    """
    receipt_data = {
        'Vendor Name': None,
        'Receipt Number': None,
        'Date': None,
        'Payment Amount': None,
        'Tax': None,
        'Payment Method': None
    }

    # Vendor Name: Assuming the vendor name appears at the top of the receipt
    vendor_match = re.search(r'^\s*(\D+)\s*$', text, re.MULTILINE)
    if vendor_match:
        receipt_data['Vendor Name'] = vendor_match.group(1).strip()

    # Receipt Number: Look for keywords like 'Receipt No.' or similar
    receipt_number_match = re.search(r'(Receipt|Invoice|Order|)\s*(No|#):?\s*(\d+)', text, re.IGNORECASE)
    if receipt_number_match:
        receipt_data['Receipt Number'] = receipt_number_match.group(3)

    # Date: Look for standard date formats like MM/DD/YYYY or DD/MM/YYYY
    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
    if date_match:
        receipt_data['Date'] = date_match.group(1)

    # Payment Amount: Look for 'Total' or 'Amount Paid' followed by a currency symbol and value
    payment_amount_match = re.search(r'(Total|Amount Paid|Grand Total|Payment):?\s*[\₹$€]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
    if payment_amount_match:
        receipt_data['Payment Amount'] = payment_amount_match.group(2)

    # Tax: Look for 'Tax' followed by an amount
    tax_match = re.search(r'(Tax|gst)\s*[\$₹€]?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
    if tax_match:
        receipt_data['Tax'] = tax_match.group(1)

    # Payment Method: Look for common payment methods like 'CASH', 'CARD', 'CREDIT', etc.
    payment_method_match = re.search(r'(CASH|CARD|CREDIT|DEBIT|VISA|UPI|Online)', text, re.IGNORECASE)
    if payment_method_match:
        receipt_data['Payment Method'] = payment_method_match.group(1).upper()

    return receipt_data


@app.post("/upload_receipt/")
async def upload_receipt(file: UploadFile = File(...)):
    """
    Endpoint to upload the receipt image, extract text from it, and process receipt data.
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")

    try:
        # Save the uploaded file
        file_path = save_uploaded_file(file)

        # Extract text from the image
        text_data = extract_text_from_image(file_path)
        print(text_data)
        if text_data == "":
            raise Exception("Please Upload valid or clear image")
        # Process the extracted text to extract receipt-specific data
        receipt_data = extract_receipt_data(text_data)

        return {
            "receipt_data": receipt_data,
            "temp_file_path": file_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing receipt: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
