"""Business Deal Evaluator API endpoints."""

from fastapi import APIRouter, HTTPException

from app.services.business_evaluator import (
    CalculateRequest,
    DealMetrics,
    INDUSTRIES,
    evaluate_deal,
)

router = APIRouter(prefix="/business-eval", tags=["Business Evaluator"])


@router.get("/industries")
async def list_industries() -> list[str]:
    """Return supported industry names for benchmarking."""
    return INDUSTRIES


@router.post("/calculate", response_model=DealMetrics)
async def calculate_deal(req: CalculateRequest) -> DealMetrics:
    """Calculate financial metrics and score for a business deal."""
    if req.asking_price <= 0:
        raise HTTPException(status_code=422, detail="asking_price must be positive")
    if req.revenue <= 0:
        raise HTTPException(status_code=422, detail="revenue must be positive")
    if req.cash_flow <= 0:
        raise HTTPException(status_code=422, detail="cash_flow must be positive")
    if req.rate_pct <= 0:
        raise HTTPException(status_code=422, detail="rate_pct must be positive")
    if req.term_years <= 0:
        raise HTTPException(status_code=422, detail="term_years must be positive")
    if not (0 < req.down_payment_pct <= 100):
        raise HTTPException(status_code=422, detail="down_payment_pct must be between 1 and 100")
    return evaluate_deal(req)
