"""Business deal evaluator — financial calculations and scoring."""

from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Industry benchmarks
# ---------------------------------------------------------------------------

INDUSTRY_BENCHMARKS: dict[str, dict] = {
    "Laundromats and Coin Laundry": {
        "cf_multiple": 2.8,
        "revenue_multiple": 0.90,
        "cf_margin": 0.29,
        "default_rate": 0.020,
    },
    "Restaurants": {
        "cf_multiple": 2.5,
        "revenue_multiple": 0.45,
        "cf_margin": 0.15,
        "default_rate": 0.055,
    },
    "Retail": {
        "cf_multiple": 2.3,
        "revenue_multiple": 0.35,
        "cf_margin": 0.12,
        "default_rate": 0.042,
    },
    "Auto Repair": {
        "cf_multiple": 3.0,
        "revenue_multiple": 0.65,
        "cf_margin": 0.22,
        "default_rate": 0.030,
    },
    "Gas Stations / Convenience Stores": {
        "cf_multiple": 2.5,
        "revenue_multiple": 0.25,
        "cf_margin": 0.08,
        "default_rate": 0.033,
    },
    "Hair Salons / Barber Shops": {
        "cf_multiple": 2.2,
        "revenue_multiple": 0.55,
        "cf_margin": 0.20,
        "default_rate": 0.040,
    },
    "Car Washes": {
        "cf_multiple": 3.5,
        "revenue_multiple": 1.10,
        "cf_margin": 0.32,
        "default_rate": 0.025,
    },
    "Dry Cleaners": {
        "cf_multiple": 2.4,
        "revenue_multiple": 0.60,
        "cf_margin": 0.22,
        "default_rate": 0.035,
    },
    "Medical / Dental Practices": {
        "cf_multiple": 3.5,
        "revenue_multiple": 0.80,
        "cf_margin": 0.22,
        "default_rate": 0.018,
    },
    "E-Commerce": {
        "cf_multiple": 3.2,
        "revenue_multiple": 0.70,
        "cf_margin": 0.18,
        "default_rate": 0.028,
    },
    "General": {
        "cf_multiple": 3.0,
        "revenue_multiple": 0.65,
        "cf_margin": 0.20,
        "default_rate": 0.030,
    },
}

INDUSTRIES = list(INDUSTRY_BENCHMARKS.keys())


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CalculateRequest(BaseModel):
    asking_price: float
    revenue: float
    cash_flow: float
    industry: str = "General"
    financing_type: str = "SBA"      # "SBA" | "Custom"
    rate_pct: float = 10.0           # annual interest rate %
    term_years: int = 10
    down_payment_pct: float = 10.0   # % of asking price
    seller_financing: float = 0.0    # additional seller note amount
    additional_expenses: float = 0.0  # annual extra expenses


class ScoreBreakdown(BaseModel):
    cf_multiple_pts: int
    cf_multiple_max: int
    dscr_pts: int
    dscr_max: int
    payback_pts: int
    payback_max: int
    cf_margin_pts: int
    cf_margin_max: int


class DealMetrics(BaseModel):
    # Inputs
    asking_price: float
    revenue: float
    cash_flow: float
    adjusted_cash_flow: float        # after additional expenses

    # Multiples
    cf_multiple: float
    revenue_multiple: float
    cf_margin_pct: float

    # Industry benchmarks
    industry: str
    industry_cf_multiple: float
    industry_revenue_multiple: float
    industry_cf_margin_pct: float
    industry_default_rate_pct: float

    # Financing
    down_payment: float
    sba_guaranty_fee: float
    total_acquisition_cost: float
    total_cash_down: float
    total_debt: float
    monthly_payment: float
    annual_payment: float

    # Performance
    dscr: float
    payback_years: float
    net_annual_cf_after_debt: float

    # Score
    score: int
    grade: str
    grade_label: str
    score_breakdown: ScoreBreakdown
    deal_summary: str


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------

def _monthly_payment(principal: float, annual_rate_pct: float, term_years: int) -> float:
    if principal <= 0:
        return 0.0
    r = annual_rate_pct / 100 / 12
    n = term_years * 12
    if r == 0:
        return principal / n
    factor = r * (1 + r) ** n / ((1 + r) ** n - 1)
    return principal * factor


def _sba_guaranty_fee(loan_amount: float) -> float:
    """Approximation of SBA 7(a) guaranty fee (charged on guaranteed portion)."""
    if loan_amount <= 0:
        return 0.0
    if loan_amount <= 150_000:
        return loan_amount * 0.85 * 0.02
    elif loan_amount <= 700_000:
        return loan_amount * 0.75 * 0.03
    else:
        return loan_amount * 0.75 * 0.035


def _score_cf_multiple(cf_multiple: float) -> int:
    if cf_multiple < 2.0:
        return 25
    if cf_multiple < 2.5:
        return 22
    if cf_multiple < 3.0:
        return 18
    if cf_multiple < 3.5:
        return 13
    if cf_multiple < 4.5:
        return 7
    return 2


def _score_dscr(dscr: float) -> int:
    if dscr >= 2.5:
        return 30
    if dscr >= 2.0:
        return 25
    if dscr >= 1.5:
        return 20
    if dscr >= 1.25:
        return 13
    if dscr >= 1.0:
        return 6
    return 0


def _score_payback(payback_years: float) -> int:
    if payback_years < 1.5:
        return 25
    if payback_years < 2.5:
        return 21
    if payback_years < 3.5:
        return 15
    if payback_years < 5.0:
        return 9
    return 3


def _score_cf_margin(cf_margin: float) -> int:
    if cf_margin >= 0.40:
        return 20
    if cf_margin >= 0.30:
        return 16
    if cf_margin >= 0.20:
        return 12
    if cf_margin >= 0.10:
        return 7
    return 2


def _grade(score: int) -> tuple[str, str]:
    if score >= 85:
        return "A", "Excellent Deal"
    if score >= 70:
        return "B", "Good Deal"
    if score >= 55:
        return "C", "Fair Deal"
    if score >= 40:
        return "D", "Risky Deal"
    return "F", "Pass on This"


def _deal_summary(metrics: dict) -> str:
    parts = []
    dscr = metrics["dscr"]
    cf_mult = metrics["cf_multiple"]
    payback = metrics["payback_years"]
    ind_cf_mult = metrics["industry_cf_multiple"]

    if dscr >= 1.5:
        parts.append(f"Strong cash flow coverage (DSCR {dscr:.2f}) means the business comfortably services its debt.")
    elif dscr >= 1.25:
        parts.append(f"Adequate DSCR of {dscr:.2f} meets SBA minimums but leaves little cushion.")
    else:
        parts.append(f"Low DSCR of {dscr:.2f} — the business may struggle to cover debt payments.")

    if cf_mult < ind_cf_mult:
        parts.append(f"Asking price multiple of {cf_mult:.2f}x is below the {metrics['industry']} industry average of {ind_cf_mult:.2f}x — priced attractively.")
    elif cf_mult > ind_cf_mult * 1.2:
        parts.append(f"Asking price multiple of {cf_mult:.2f}x exceeds the industry average of {ind_cf_mult:.2f}x — consider negotiating down.")
    else:
        parts.append(f"Asking price multiple of {cf_mult:.2f}x is in line with the {metrics['industry']} industry average.")

    if payback < 2.5:
        parts.append(f"Short payback period of {payback:.1f} years on your cash down.")
    else:
        parts.append(f"Payback period of {payback:.1f} years — factor in your risk tolerance.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def evaluate_deal(req: CalculateRequest) -> DealMetrics:
    benchmarks = INDUSTRY_BENCHMARKS.get(req.industry, INDUSTRY_BENCHMARKS["General"])

    adjusted_cf = req.cash_flow - req.additional_expenses

    # Multiples
    cf_multiple = req.asking_price / adjusted_cf if adjusted_cf > 0 else 0.0
    revenue_multiple = req.asking_price / req.revenue if req.revenue > 0 else 0.0
    cf_margin = req.cash_flow / req.revenue if req.revenue > 0 else 0.0

    # Financing
    down_payment = req.asking_price * req.down_payment_pct / 100
    bank_loan = req.asking_price - down_payment - req.seller_financing
    bank_loan = max(bank_loan, 0.0)

    guaranty_fee = _sba_guaranty_fee(bank_loan) if req.financing_type == "SBA" else 0.0

    total_cash_down = down_payment + guaranty_fee
    total_debt = bank_loan + req.seller_financing
    total_acquisition_cost = req.asking_price + guaranty_fee

    bank_monthly = _monthly_payment(bank_loan, req.rate_pct, req.term_years)
    # Seller financing typically shorter term / lower rate; use same rate for simplicity
    seller_monthly = _monthly_payment(req.seller_financing, req.rate_pct, min(req.term_years, 5))
    monthly_payment = bank_monthly + seller_monthly
    annual_payment = monthly_payment * 12

    dscr = adjusted_cf / annual_payment if annual_payment > 0 else float("inf")
    net_annual_cf = adjusted_cf - annual_payment
    payback_years = total_cash_down / adjusted_cf if adjusted_cf > 0 else float("inf")

    # Score
    cf_pts = _score_cf_multiple(cf_multiple)
    dscr_pts = _score_dscr(dscr)
    pay_pts = _score_payback(payback_years)
    margin_pts = _score_cf_margin(cf_margin)
    total_score = cf_pts + dscr_pts + pay_pts + margin_pts

    grade, grade_label = _grade(total_score)

    summary_ctx = {
        "dscr": dscr,
        "cf_multiple": cf_multiple,
        "payback_years": payback_years,
        "industry": req.industry,
        "industry_cf_multiple": benchmarks["cf_multiple"],
    }

    return DealMetrics(
        asking_price=req.asking_price,
        revenue=req.revenue,
        cash_flow=req.cash_flow,
        adjusted_cash_flow=adjusted_cf,
        cf_multiple=round(cf_multiple, 2),
        revenue_multiple=round(revenue_multiple, 2),
        cf_margin_pct=round(cf_margin * 100, 1),
        industry=req.industry,
        industry_cf_multiple=benchmarks["cf_multiple"],
        industry_revenue_multiple=benchmarks["revenue_multiple"],
        industry_cf_margin_pct=round(benchmarks["cf_margin"] * 100, 1),
        industry_default_rate_pct=round(benchmarks["default_rate"] * 100, 2),
        down_payment=round(down_payment, 2),
        sba_guaranty_fee=round(guaranty_fee, 2),
        total_acquisition_cost=round(total_acquisition_cost, 2),
        total_cash_down=round(total_cash_down, 2),
        total_debt=round(total_debt, 2),
        monthly_payment=round(monthly_payment, 2),
        annual_payment=round(annual_payment, 2),
        dscr=round(dscr, 2) if dscr != float("inf") else 999.0,
        payback_years=round(payback_years, 2) if payback_years != float("inf") else 999.0,
        net_annual_cf_after_debt=round(net_annual_cf, 2),
        score=total_score,
        grade=grade,
        grade_label=grade_label,
        score_breakdown=ScoreBreakdown(
            cf_multiple_pts=cf_pts,
            cf_multiple_max=25,
            dscr_pts=dscr_pts,
            dscr_max=30,
            payback_pts=pay_pts,
            payback_max=25,
            cf_margin_pts=margin_pts,
            cf_margin_max=20,
        ),
        deal_summary=_deal_summary(summary_ctx),
    )
