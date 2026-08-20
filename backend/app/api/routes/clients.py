from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("")
async def list_clients() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Client persistence is not implemented in the scaffold.",
    )


@router.get("/{client_id}")
async def get_client(client_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Client lookup is not implemented for {client_id}.",
    )
