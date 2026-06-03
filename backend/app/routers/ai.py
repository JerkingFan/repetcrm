from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models import User
from app.services.homework_ai import get_ai_status

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
async def ai_status(_user: User = Depends(get_current_user)):
    return await get_ai_status()


@router.get("/config")
def ai_config(_user: User = Depends(get_current_user)):
    """Что реально читает backend из backend/.env прямо сейчас."""
    from app.config import _ENV_FILE, get_settings

    s = get_settings()
    from dotenv import dotenv_values

    raw = dotenv_values(_ENV_FILE) if _ENV_FILE.is_file() else {}
    return {
        "env_file": str(_ENV_FILE),
        "homework_ai_provider": s.homework_ai_provider,
        "homework_ai_provider_in_file": (raw.get("HOMEWORK_AI_PROVIDER") or "").strip(),
        "openrouter_model": s.openrouter_model,
        "openrouter_model_in_file": (raw.get("OPENROUTER_MODEL") or "").strip(),
        "openrouter_configured": bool(s.openrouter_api_key.strip()),
    }
