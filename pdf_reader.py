import PyPDF2

def read_pdf(file_path):
    """
    Read a PDF file and return its content as a string.
    
    :param file_path: Path to the PDF file
    :return: String containing the text content of the PDF
    """
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        
        for page in pdf_reader.pages:
            text += page.extract_text()
        
    return text

def print_pdf_input_fields(file_path):
    """
    Print the input fields available in the PDF.
    
    :param file_path: Path to the PDF file
    """
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        if '/AcroForm' in pdf_reader.trailer['/Root']:
            pdf_fields = pdf_reader.get_fields()
            
            if pdf_fields:
                print("Input fields found in the PDF:")
                for field_name, field_value in pdf_fields.items():
                    print(f"Field Name: {field_name}")
                    print(f"Field Type: {field_value.get('/FT', 'Unknown')}")
                    print(f"Field Value: {field_value.get('/V', 'Empty')}")
                    print("-" * 30)
            else:
                print("No input fields found in the PDF.")
        else:
            print("This PDF does not contain any fillable forms.")

if __name__ == "__main__":
    pdf_path = "available-pdfs/avivaalberta.pdf"
    
    # Read and print PDF content
    pdf_content = read_pdf(pdf_path)
    print("PDF Content:")
    print(pdf_content)
    
    print("\n" + "=" * 50 + "\n")
    
    # Print input fields
    print_pdf_input_fields(pdf_path)