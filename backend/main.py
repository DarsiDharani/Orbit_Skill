import sys
import os

# --- ADDED: Fix ModuleNotFoundError: No module named 'app' ---
# This ensures the directory containing 'app' (which is 'backend') is on the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))) 
# -------------------------------------------------------------

import logging
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.routes import register, login, dashboard_routes, additional_skills, training_routes, assignment_routes, training_requests, shared_content_routes
from app.database import AsyncSessionLocal, create_db_and_tables
from app.excel_loader import load_all_from_excel, load_manager_employee_from_csv

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI App Initialization ---
app = FastAPI(
    title="SkillOrbit API",
    description="API for managing skills and training data.",
    version="1.0.0"
)

# --- CORS Middleware ---
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- API Routers ---
app.include_router(register.router)
app.include_router(login.router)
app.include_router(dashboard_routes.router)
app.include_router(additional_skills.router)
app.include_router(training_routes.router)
app.include_router(assignment_routes.router)
app.include_router(training_requests.router)
app.include_router(shared_content_routes.router)

# <<< NEW: Root Endpoint for Welcome Message >>>
@app.get("/", tags=["Default"])
async def read_root():
    """
    A simple welcome message to confirm the API is running.
    """
    return {"message": "Welcome to the SkillOrbit API. Please go to /docs for the API documentation."}

# <<< PERMANENT SOLUTION: File Upload Endpoint >>>
@app.post("/upload-and-refresh", status_code=200, tags=["Admin"])
async def upload_and_refresh_data(file: UploadFile = File(...)):
    """
    Accepts an Excel file upload, reads its content in memory, and refreshes the database.
    """
    logging.info(f"API: Received file '{file.filename}' for data refresh.")

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an Excel file.")

    try:
        async with AsyncSessionLocal() as db:
            await load_all_from_excel(file.file, db)
            
            # Verify data was inserted
            from sqlalchemy import select, func
            from app.models import Trainer, TrainingDetail, EmployeeCompetency
            
            trainers_result = await db.execute(select(func.count(Trainer.id)))
            trainers_count = trainers_result.scalar()
            trainings_result = await db.execute(select(func.count(TrainingDetail.id)))
            trainings_count = trainings_result.scalar()
            competencies_result = await db.execute(select(func.count(EmployeeCompetency.id)))
            competencies_count = competencies_result.scalar()
        
        logging.info(f"Successfully processed and loaded data from '{file.filename}'.")
        return {
            "message": f"Data from '{file.filename}' has been successfully uploaded and the database has been refreshed.",
            "trainers_inserted": trainers_count,
            "trainings_inserted": trainings_count,
            "employee_competencies_inserted": competencies_count,
            "status": "success"
        }
    
    except ValueError as ve:
        # This is raised when all rows are skipped
        logging.error(f"Validation error: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"An error occurred during file processing and database refresh: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.post("/upload-manager-employee-csv", status_code=200, tags=["Admin"])
async def upload_manager_employee_csv(file: UploadFile = File(...)):
    """
    Accepts a CSV file upload for manager-employee relationships and loads it into the database.
    Expected CSV columns: manager_empid, manager_name, employee_empid, employee_name, 
                         manager_is_trainer, employee_is_trainer
    """
    logging.info(f"API: Received CSV file '{file.filename}' for manager-employee data load.")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    try:
        async with AsyncSessionLocal() as db:
            await load_manager_employee_from_csv(file.file, db)
            
            # Verify data was inserted
            from sqlalchemy import select, func
            from app.models import ManagerEmployee
            
            # Count all manager-employee relationships
            count_result = await db.execute(
                select(func.count()).select_from(ManagerEmployee)
            )
            total_count = count_result.scalar()
        
        logging.info(f"Successfully processed and loaded manager-employee data from '{file.filename}'.")
        return {
            "message": f"Manager-employee data from '{file.filename}' has been successfully uploaded and the database has been refreshed.",
            "relationships_inserted": total_count,
            "status": "success"
        }
    
    except ValueError as ve:
        logging.error(f"Validation error: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"An error occurred during CSV file processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


# --- Application Lifecycle Events ---
@app.on_event("startup")
async def on_startup():
    """
    This function runs when the FastAPI application starts.
    """
    logging.info("STARTUP: Initializing database...")
    await create_db_and_tables()
    logging.info("STARTUP: Database initialization complete.")
    logging.info("STARTUP: Server is ready. Please go to /docs for the API documentation and to upload data.")