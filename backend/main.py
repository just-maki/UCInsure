from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # CHANGE THIS PART EACH TIEM YOU RERUN FRONTEND
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"message": "Backend is running"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    print(f"[UPLOAD] Saved: {file.filename}") 

    return {
        "filename": file.filename,
        "status": "uploaded"
    }

@app.post("/analyze")
async def analyze(files: list[str]):
    # placeholder for ML logic later
    return {
        "message": "analysis started",
        "files_received": files
    }