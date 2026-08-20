from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/google-sheets/sync")
async def sync_google_sheets() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google Sheets import is not implemented in the scaffold.",
    )


@router.get("/{import_id}")
async def get_import(import_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Import run lookup is not implemented for {import_id}.",
    )
