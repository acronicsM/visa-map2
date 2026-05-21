from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_api_key
from app.schemas.country_profile import CountryProfileUploadResponse
from app.services.country_profile_service import import_country_profiles_from_file

router = APIRouter(
    prefix="/admin/country-profiles",
    tags=["admin"],
    dependencies=[Depends(require_api_key)],
)


@router.put("", response_model=CountryProfileUploadResponse)
async def put_country_profiles(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """
    Загрузка country_profile.json через multipart/form-data.
    Полная замена exotic-пар по каждой home_iso2 из файла; профили — UPSERT.
    """
    try:
        return await import_country_profiles_from_file(db, file)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
