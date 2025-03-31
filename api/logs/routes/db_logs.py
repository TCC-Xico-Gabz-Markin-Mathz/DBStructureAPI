from fastapi import APIRouter


router = APIRouter(prefix="/db_logs", tags=["db_logs"])


@router.post("/")
def update_db_structure():
    return True
