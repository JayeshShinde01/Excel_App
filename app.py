from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os

app = FastAPI(title="Excel Search API")

# ✅ CORS (for React frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
CURRENT_FILE = os.path.join(DATA_DIR, "current.xlsx")

# Global cache
df_cache: pd.DataFrame | None = None


# ================= ADMIN =================
@app.post("/admin/upload-excel/")
async def upload_excel(file: UploadFile = File(...)):
    global df_cache

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files allowed")

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(CURRENT_FILE, "wb") as f:
        f.write(await file.read())

    df_cache = pd.read_excel(CURRENT_FILE)

    return {
        "status": "success",
        "rows": len(df_cache),
        "columns": list(df_cache.columns),
    }


# ================= USER =================
@app.get("/user/search-imei/")
async def search_imei(imei: str):
    global df_cache

    # Reload after restart
    if df_cache is None:
        if not os.path.exists(CURRENT_FILE):
            raise HTTPException(status_code=400, detail="No Excel uploaded by admin")
        df_cache = pd.read_excel(CURRENT_FILE)

    # Detect IMEI column
    imei_col = None
    for col in df_cache.columns:
        if col.strip().lower() in ["imei", "imei no", "imei_no", "imeino"]:
            imei_col = col
            break

    if not imei_col:
        raise HTTPException(status_code=400, detail="IMEI column not found")

    df = df_cache.copy()
    df[imei_col] = df[imei_col].astype(str).str.strip()

    result = df[df[imei_col] == imei.strip()]

    return {
        "count": len(result),
        "data": result.to_dict(orient="records")
    }


# ================= STATUS =================
@app.get("/excel-status/")
async def excel_status():
    global df_cache

    if df_cache is None and os.path.exists(CURRENT_FILE):
        df_cache = pd.read_excel(CURRENT_FILE)

    if df_cache is None:
        return {"uploaded": False}

    return {
        "uploaded": True,
        "rows": len(df_cache),
        "columns": list(df_cache.columns),
    }
