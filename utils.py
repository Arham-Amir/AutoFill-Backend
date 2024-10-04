from datetime import datetime
import fitz  # PyMuPDF
import re
import pdfrw
import io


def extract_info(text):
    info = {}
    
    patterns = {
        "claim_number": r"CLAIM:\s*(\S+)",
        "policy_number": r"POLICY\s*(\S+)",
        "company_name": r"ADJUSTER\s*(.+)",
        "date_of_loss": r"DATE OF LOSS\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        "owner_name": r"OWNER\s*(.+)",
        "owner_address": r"ADDRESS\s*(.+)",
        "city_province_postal": r"ADDRESS\s*[\s\S]*?\n([\w\s]+(?:\s+[A-Z]{2}\s+\w{1}\d{1}\w{1}\s*\d{1}\w{1}\d{1})?)",  # Updated regex for city, province, postal
        "phone_number": r"CONTACT METHODS\s*([\d-]+)",  # Updated regex to capture full phone number
        "vin": r"VIN\s*(\S+)",
        "make_model_year": r"VEHICLE:\s*(\d{4})\s+(.+)",
        "color": r"COLOR\s*(.+)",
        "mileage": r"MILEAGE\s*(\d+)",
        "license_plate": r"LICENSE PLATE\s*\n([A-Z0-9\s]+)\n",
        "assignment_sent_date": r"ASSIGNMENT SENT:\s*(\d{2}/\d{2}/\d{4})",
        "adjuster_email": r"([A-Za-z0-9._%+-]+@aviva\.com)",  # Updated Aviva-specific email regex
    }
    
    for key, pattern in patterns.items():
        if key == "adjuster_email":
            # For adjuster email, search the entire text
            match = re.search(pattern, text, re.IGNORECASE)
            print("adjuster_email: ", match)
        else:
            # For other patterns, keep the existing behavior
            match = re.search(pattern, text)
        
        if match:
            info[key] = match.group(1).strip()
    # Extract make and model year separately
    make_model_year_match = re.search(patterns["make_model_year"], text)
    if make_model_year_match:
        info["model_year"] = make_model_year_match.group(1).strip()
        info["make"] = make_model_year_match.group(2).strip()
    
    return info

def process_extracted_info(extracted_info):
    claim_number = extracted_info.get("claim_number", "")
    policy_number = extracted_info.get("policy_number", "")
    company_name = extracted_info.get("company_name", "")
    date_of_loss = extracted_info.get("date_of_loss", "")
    
    # Update date processing to handle the new format
    if date_of_loss:
        dol_parts = date_of_loss.split('/')
        if len(dol_parts) == 3:
            month, day, year = dol_parts
            # Ensure year is in four-digit format
            if len(year) == 2:
                year = '20' + year
            date_of_loss = f"{month}/{day}/{year}"
    
    owner_name = extracted_info.get("owner_name", "")
    owner_address = extracted_info.get("owner_address", "")
    city_province_postal = extracted_info.get("city_province_postal", "")
    phone_number = extracted_info.get("phone_number", "")
    vin = extracted_info.get("vin", "")
    make = extracted_info.get("make", "")
    model_year = extracted_info.get("model_year", "")
    color = extracted_info.get("color", "")
    mileage = extracted_info.get("mileage", "")
    license_plate = extracted_info.get("license_plate", "")
    assignment_sent_date = extracted_info.get("assignment_sent_date", "")
    adjuster_email = extracted_info.get("adjuster_email", "")

    # Process city_province_postal
    split_text = city_province_postal.split("CONTACT")[0]
    post_code = ' '.join(split_text.split()[-2:])
    city = ' '.join(split_text.split()[:-2])
    state_prefix = city.split()[-1]

    vin = '    '.join(vin)

    current_date = datetime.now()
    day = current_date.strftime("%d").lstrip('0')
    month = current_date.strftime("%m").lstrip('0')
    year = current_date.strftime("%y")
    formatted_date = f"{day}/{month}/{year}"


    return {
        'claim_number': claim_number,
        'policy_number': policy_number,
        'company_name': company_name,
        'date_of_loss': date_of_loss,
        'owner_name': owner_name,
        'owner_address': owner_address,
        'city': city,
        'post_code': post_code,
        'state_prefix': state_prefix,
        'phone_number': phone_number,
        'vin': vin,
        'make': make,
        'model_year': model_year,
        'color': color,
        'mileage': mileage,
        'license_plate': license_plate,
        'assignment_sent_date': assignment_sent_date,
        'adjuster_email': adjuster_email,
        'formatted_date': formatted_date
    }

def fill_pdf_form(template_path, values_to_fill):
    template_pdf = pdfrw.PdfReader(template_path)
    
    for page in template_pdf.pages:
        annotations = page.get('/Annots')
        if annotations:
            for annotation in annotations:
                if annotation['/T']:
                    field_name = annotation['/T'][1:-1]
                    if field_name in values_to_fill:
                        value = values_to_fill[field_name]
                        if field_name == 'Text24':
                            # Remove spaces and set the value
                            value = value.replace(" ", "")
                            annotation.update(
                                pdfrw.PdfDict(V='{}'.format(value), AS='{}'.format(value))
                            )
                            # Remove the existing appearance stream
                            if '/AP' in annotation:
                                del annotation['/AP']
                        else:
                            # For other fields, keep the existing behavior
                            annotation.update(pdfrw.PdfDict(V='{}'.format(value)))
                            if field_name in ['Vehicle Identification Number', 'Name', 'Text79']:
                                annotation.update(pdfrw.PdfDict(AP='{}'.format(value)))

    output_buffer = io.BytesIO()
    pdfrw.PdfWriter().write(output_buffer, template_pdf)
    output_buffer.seek(0)
    
    return output_buffer
