from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.background import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import tempfile
import os
import fitz
from datetime import datetime

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import AUTH_USERNAME, AUTH_PASSWORD, ACCESS_TOKEN_EXPIRE_MINUTES
from pdf_processing import extract_info, process_extracted_info, create_values_to_fill, fill_pdf_form
from auth import create_access_token, get_current_user
from models import Token, User
from datetime import timedelta

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process_vehicle_form/")
async def process_vehicle_form(
    file: UploadFile = File(...),
    filename: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Processing vehicle form for user: {current_user.username}")

    if not filename.lower().endswith(".pdf"):
        logger.warning(f"Invalid file type uploaded by user: {current_user.username}")
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")

    try:
        pdf_content = await file.read()
        doc = fitz.open(stream=pdf_content, filetype="pdf")
    except Exception as e:
        logger.error(f"Failed to read PDF file for user {current_user.username}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to read PDF file: {str(e)}")

    try:
        page = doc.load_page(0)
        text = page.get_text()
        extracted_info = extract_info(text)
        processed_info = process_extracted_info(extracted_info)
        values_to_fill = create_values_to_fill(processed_info)

        template_path = "Input_vehicle_ontario_pdf/to_be_filled.pdf"
        filled_pdf = fill_pdf_form(template_path, values_to_fill)

        doc.close()

        # Generate output filename
        output_filename = f"{filename.rsplit('.', 1)[0]}-output.pdf"

        # Create a temporary file to store the filled PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(filled_pdf.getvalue())
            temp_file_path = temp_file.name

        # Use background_tasks to unlink the temp file
        background_tasks.add_task(os.unlink, temp_file_path)

        logger.info(f"Successfully processed vehicle form for user: {current_user.username}")

        # Return the temporary file as a FileResponse with the new filename
        return FileResponse(temp_file_path, media_type="application/pdf", filename=output_filename)
    except Exception as e:
        logger.error(f"Error processing vehicle form for user {current_user.username}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing the vehicle form")

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"Received token request for username: {form_data.username}")
    
    if form_data.username != AUTH_USERNAME or form_data.password != AUTH_PASSWORD:
        logger.warning(f"Failed login attempt for username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    try:
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        logger.info(f"Successfully created access token for username: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token",
        )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP error occurred: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error occurred: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"An unexpected error occurred: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )