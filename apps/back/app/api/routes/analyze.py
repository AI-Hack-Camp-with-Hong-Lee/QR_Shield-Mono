from fastapi import APIRouter, Depends

from app.schemas.analysis import AnalyzeUrlRequest, ScanResultResponse
from app.services.risk_engine import RiskAnalysisService, get_risk_analysis_service


router = APIRouter()


@router.post("/analyze", response_model=ScanResultResponse)
def analyze_url(
    payload: AnalyzeUrlRequest,
    service: RiskAnalysisService = Depends(get_risk_analysis_service),
) -> ScanResultResponse:
    return service.analyze(payload.url)

