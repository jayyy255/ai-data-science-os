from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from services.storage.factory import get_storage_provider
import io

router = APIRouter(prefix="/api/test", tags=["test"])

@router.post("/upload")
async def test_upload(file: UploadFile = File(...)):
    storage = get_storage_provider()
    try:
        content = await file.read()
        # Upload using upload_dataset
        path = storage.upload_dataset(file.filename, content)
        return {"status": "success", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

@router.get("/download")
async def test_download(path: str):
    storage = get_storage_provider()
    try:
        content = storage.download_file(path)
        filename = path.split("/")[-1]
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage download failed: {e}")
