"""Read-only UI routes."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from kal_predict.api.state import get_ui_service
from kal_predict.services.ui_data import UIDataService

router = APIRouter(prefix="/api/ui", tags=["ui"])
trial_router = APIRouter(prefix="/api/trial", tags=["trial"])


class TrialManualBetRequest(BaseModel):
    market_id: str = Field(pattern=r"^[A-Z0-9_]+$")
    side: Literal["YES", "NO"]
    contracts: int = Field(default=1, ge=1, le=1000)


class TrialAutoBetRequest(BaseModel):
    market_id: str = Field(pattern=r"^[A-Z0-9_]+$")
    contracts: int = Field(default=1, ge=1, le=1000)


class TrialScenarioItem(BaseModel):
    market_id: str = Field(pattern=r"^[A-Z0-9_]+$")
    mode: Literal["manual", "auto"] = "auto"
    side: Optional[Literal["YES", "NO"]] = None
    contracts: int = Field(default=1, ge=1, le=1000)


class TrialScenarioRunRequest(BaseModel):
    dry_run: bool = True
    scenarios: list[TrialScenarioItem] = Field(default_factory=list, max_length=20)


@router.get("/health")
async def health(service: UIDataService = Depends(get_ui_service)) -> dict:
    return await service.health()


@router.get("/markets")
async def markets(
    limit: int = Query(default=50, ge=1, le=500),
    service: UIDataService = Depends(get_ui_service),
) -> dict:
    return await service.markets(limit=limit)


@router.get("/decisions")
async def decisions(
    limit: int = Query(default=100, ge=1, le=1000),
    market_id: Optional[str] = Query(default=None),
    service: UIDataService = Depends(get_ui_service),
) -> dict:
    return await service.decisions(limit=limit, market_id=market_id)


@router.get("/metrics/replay")
async def replay_metrics(service: UIDataService = Depends(get_ui_service)) -> dict:
    return await service.replay_metrics()


@router.get("/inference-health")
async def inference_health(service: UIDataService = Depends(get_ui_service)) -> dict:
    return await service.inference_health()


@router.get("/trial-decision-trace")
async def trial_decision_trace(
    limit: int = Query(default=20, ge=1, le=200),
    service: UIDataService = Depends(get_ui_service),
) -> dict:
    return await service.trial_decision_trace(limit=limit)


@router.get("/metrics/paper")
async def paper_metrics(service: UIDataService = Depends(get_ui_service)) -> dict:
    return await service.paper_metrics()


@router.get("/audit")
async def audit(
    trace_id: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    service: UIDataService = Depends(get_ui_service),
) -> dict:
    return await service.audit(trace_id=trace_id, level=level, limit=limit)


@trial_router.get("/markets")
async def trial_markets(
    limit: int = Query(default=50, ge=1, le=200),
    service: UIDataService = Depends(get_ui_service),
) -> dict:
    return await service.trial_markets(limit=limit)


@trial_router.get("/book")
async def trial_book(service: UIDataService = Depends(get_ui_service)) -> dict:
    return await service.trial_book()


@trial_router.post("/bets/manual")
async def trial_manual_bet(
    payload: TrialManualBetRequest,
    service: UIDataService = Depends(get_ui_service),
) -> dict:
    result = await service.trial_manual_bet(
        market_id=payload.market_id,
        side=payload.side,
        contracts=payload.contracts,
    )
    if not result.get("ok"):
        return JSONResponse(status_code=400, content=result)
    return result


@trial_router.post("/bets/auto")
async def trial_auto_bet(
    payload: TrialAutoBetRequest,
    service: UIDataService = Depends(get_ui_service),
) -> dict:
    result = await service.trial_auto_bet(
        market_id=payload.market_id,
        contracts=payload.contracts,
    )
    if not result.get("ok"):
        return JSONResponse(status_code=400, content=result)
    return result


@trial_router.post("/scenarios/run")
async def trial_scenarios_run(
    payload: TrialScenarioRunRequest,
    service: UIDataService = Depends(get_ui_service),
) -> dict:
    result = await service.run_trial_scenarios(
        scenarios=[item.model_dump() for item in payload.scenarios],
        dry_run=payload.dry_run,
    )
    return result
