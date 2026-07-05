"""Analytics API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import AnalyticsOverview
from app.services.analytics_service import build_analytics_overview

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_analytics_overview(db, user.id)
