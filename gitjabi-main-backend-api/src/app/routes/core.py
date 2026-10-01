from fastapi import Depends, APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["Core"])

@router.get("/test")
def test():
    return "OK"
