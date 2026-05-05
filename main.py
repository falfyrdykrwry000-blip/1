import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

app = FastAPI(title="تحديث التلقائي", version="1.0.0")

# رابط ملف version.json الخام على GitHub
VERSION_URL = "https://raw.githubusercontent.com/falfyrdykrwry000-blip/storage/main/version.json"

@app.get("/")
async def root():
    return {"status": "ok", "service": "K1 Update Server"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "2026-05-05T20:00:00Z"}

@app.post("/api/v1/update/check")
async def check_update(request: Request):
    """
    يقارن إصدار التطبيق الحالي مع آخر إصدار متاح
    """
    try:
        data = await request.json()
        current_version = data.get("current_version", 0)
        
        # جلب ملف version.json من GitHub
        async with httpx.AsyncClient() as client:
            response = await client.get(VERSION_URL)
            response.raise_for_status()
            latest = response.json()
        
        latest_version = latest["latest_version"]
        update_available = latest_version > current_version
        
        return JSONResponse({
            "update_available": update_available,
            "latest_version": latest_version,
            "version_name": latest["version_name"],
            "force_update": latest["force_update"],
            "changelog": latest["changelog"],
            "file_size": latest["file_size"],
            "checksum": latest["checksum"],
            "current_version": current_version
        })
        
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "update_available": False},
            status_code=500
        )