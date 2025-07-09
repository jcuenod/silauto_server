from fastapi import APIRouter, HTTPException, Query, status

from app.state import lang_codes_controller

router = APIRouter(
    tags=["lang_codes"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=list[str])
async def get_lang_codes(
    lang_code: str = Query(
        None,
        description="Optional language code to filter results. If not provided, returns all language codes.",
    ),
):
    """
    Get language codes and their associated scripts.

    If `lang_code` is provided, returns the scripts for that specific language code.
    """
    codes = lang_codes_controller.get_by_code(lang_code)
    if not codes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language code '{lang_code}' not found.",
        )
    return codes
