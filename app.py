from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Excel Search API")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.get("/")
def home():
    return FileResponse("frontend/user.html")

@app.get("/admin")
def admin_page():
    return FileResponse("frontend/dashboard.html")


# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
CURRENT_FILE = os.path.join(DATA_DIR, "current.xlsx")

# Global DataFrame (current reference)
df_cache: pd.DataFrame | None = None




@app.post("/admin/upload-excel/")
async def upload_excel(file: UploadFile = File(...)):
    global df_cache

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files allowed")

    os.makedirs(DATA_DIR, exist_ok=True)

    # Save file (replace existing)
    with open(CURRENT_FILE, "wb") as f:
        f.write(await file.read())

    # Load into pandas
    df_cache = pd.read_excel(CURRENT_FILE)

    return {
        "status": "success",
        "message": f"{file.filename} uploaded successfully",
        "columns": list(df_cache.columns),
        "rows": len(df_cache)
    }



from fastapi import Query
@app.get("/user/search-imei/")
async def search_imei(imei: str):
    global df_cache

    # 1️⃣ Load Excel if server restarted
    if df_cache is None:
        if not os.path.exists(CURRENT_FILE):
            raise HTTPException(status_code=400, detail="No Excel uploaded by admin")
        df_cache = pd.read_excel(CURRENT_FILE)

    # 2️⃣ Find IMEI column dynamically
    imei_col = None
    for col in df_cache.columns:
        if col.strip().lower() in ["imei", "imei no", "imei_no", "imeino"]:
            imei_col = col
            break

    if not imei_col:
        raise HTTPException(status_code=400, detail="IMEI column not found in Excel")

    # 3️⃣ Clean & search
    df = df_cache.copy()
    df[imei_col] = df[imei_col].astype(str).str.strip()

    result = df[df[imei_col] == imei.strip()]

    if result.empty:
        return {
            "count": 0,
            "data": []
        }

    return {
        "count": len(result),
        "data": result.to_dict(orient="records")
    }

@app.get("/excel-status/")
async def excel_status():
    global df_cache

    if df_cache is None and os.path.exists(CURRENT_FILE):
        df_cache = pd.read_excel(CURRENT_FILE)

    if df_cache is None:
        return {
            "uploaded": False,
            "message": "No Excel file uploaded yet"
        }

    return {
        "uploaded": True,
        "columns": list(df_cache.columns),
        "rows": len(df_cache)
    }
