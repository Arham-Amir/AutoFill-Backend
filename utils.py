import re
from datetime import datetime
import pdfrw
import io

def extract_info(text):
    info = {}
    
    patterns = {
        "claim_number": r"CLAIM:\s*(\S+)",
        "policy_number": r"POLICY\s*(\S+)",
        "company_name": r"COMPANY NAME\s*(.+)",
        "date_of_loss": r"DATE OF LOSS\s*(\S+)",
        "owner_name": r"OWNER\s*(.+)",
        "owner_address": r"ADDRESS\s*(.+)",
        "city_province_postal": r"ADDRESS\s*[\s\S]*?\n([\w\s]+(?:\s+[A-Z]{2}\s+\w{1}\d{1}\w{1}\s*\d{1}\w{1}\d{1})?)",
        "phone_number": r"CONTACT METHODS\s*([\d-]+)",
        "vin": r"VIN\s*(\S+)",
        "make_model_year": r"VEHICLE:\s*(\d{4})\s+(.+)",
        "color": r"COLOR\s*(.+)",
        "mileage": r"MILEAGE\s*(\d+)",
        "license_plate": r"LICENSE PLATE\s*\n([A-Z0-9\s]+)\n",
    }
    
    for key, pattern in patterns.items():
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
        'formatted_date': formatted_date
    }

def create_values_to_fill(processed_info):
    return {
        'Holder of Vehicle Portion of the Permit, Surname and Given Names': processed_info['owner_name'],
        'Holder of Vehicle Portion of the Permit, Driver\'s Licence Number or Registrant Identification Number': '',
        'Holder of Vehicle Portion of the Permit, Box Number': processed_info['owner_address'],
        ' Box Number': processed_info['owner_address'],
        'Holder of Vehicle Portion of the Permit, Street, P.O. Box Number': processed_info['owner_address'],
        'Holder of Vehicle Portion of the Permit, City, Town or Village': processed_info['city'],
        'Holer of Vehicle Portion of the Permit, Postal Code': processed_info['post_code'],
        'Holder of Vehicle Portion of the Permit, Telephone Number': processed_info['phone_number'],
        'Vehicle Insurance, Policy Number': processed_info['policy_number'],
        'Vehicle Insurance, Claim Number': processed_info['claim_number'],
        'Vehicle Insurance, Claim Representative': processed_info['company_name'],
        'Date of Incident, Day': processed_info['date_of_loss'].split('/')[1],
        'Date of Incident, Month': processed_info['date_of_loss'].split('/')[0],
        'Date of Incident, Year': processed_info['date_of_loss'].split('/')[2],
        'Vehicle Identification Number': processed_info['vin'],
        'Vehicle Information, Make': processed_info['make'].split()[0],
        'Vehicle Information, Model': processed_info['make'].split()[1],
        'Vehicle Information, Year': processed_info['model_year'],
        r"\)": 'Auto',
        'Vehicle Information, Colour': processed_info['color'],
        'Vehicle Information, Odometer Reading': processed_info['mileage'],
        'Vehicle Information, Licence Plate': processed_info['license_plate'].split('COLOR')[0],
        'Vehicle Information, Province or State': processed_info['state_prefix'],
        'Appraisal or Inspection Contact Person, Name of Appraiser or Person Who Carried Out Inspection': 'Jason Shufford Jr',
        'Brand Determination, Appraiser\'s Name': 'Jason Shufford Jr',
        'Declaration, Print Name of Person Notifying Registrar': 'Jason Shufford Jr',
        'Declaration, Date': processed_info['formatted_date'],
        'Text22': "Jason Shufford Jr "
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
                        annotation.update(pdfrw.PdfDict(V='{}'.format(value)))
                        if field_name == 'Vehicle Identification Number':
                            annotation.update(pdfrw.PdfDict(AP='{}'.format(value)))

    output_buffer = io.BytesIO()
    pdfrw.PdfWriter().write(output_buffer, template_pdf)
    output_buffer.seek(0)
    
    return output_buffer