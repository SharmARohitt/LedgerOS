import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import CurrentUser, get_current_user, get_db
from app.domain.financial_twin.engine import gather_inputs
from app.domain.simulations.engine import SCENARIO_TYPES, run_scenario
from app.models.scenarios import Scenario

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


class CreateScenarioRequest(BaseModel):
    scenario_type: str
    params: dict = {}
    label: str = ""


def _serialize_summary(s: Scenario) -> dict:
    scenario_snapshot = json.loads(s.scenario_json)
    baseline_snapshot = json.loads(s.baseline_json)
    return {
        "id": s.id,
        "scenario_type": s.scenario_type,
        "label": s.label,
        "params": json.loads(s.input_json),
        "created_at": s.created_at.isoformat(),
        "deployable_capital_delta": round(
            scenario_snapshot["capital_map"]["deployable_capital"] - baseline_snapshot["capital_map"]["deployable_capital"], 2
        ),
    }


@router.get("")
def list_scenarios(db: Session = Depends(get_db), limit: int = 25, offset: int = 0) -> dict:
    query = db.query(Scenario)
    total = query.count()
    items = query.order_by(Scenario.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [_serialize_summary(s) for s in items], "total": total}


@router.post("")
def create_scenario(
    body: CreateScenarioRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)
) -> dict:
    if body.scenario_type not in SCENARIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"scenario_type must be one of {SCENARIO_TYPES}",
        )

    baseline_inputs = gather_inputs(db)
    result = run_scenario(baseline_inputs, body.scenario_type, body.params)

    scenario = Scenario(
        scenario_type=body.scenario_type,
        label=body.label or body.scenario_type.replace("_", " ").title(),
        input_json=json.dumps(body.params),
        baseline_json=json.dumps(result["baseline"]),
        scenario_json=json.dumps(result["scenario"]),
        created_by=user.user_id,
    )
    db.add(scenario)
    db.commit()

    return {"id": scenario.id, **result}


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str, db: Session = Depends(get_db)) -> dict:
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return {
        "id": scenario.id,
        "scenario_type": scenario.scenario_type,
        "label": scenario.label,
        "params": json.loads(scenario.input_json),
        "baseline": json.loads(scenario.baseline_json),
        "scenario": json.loads(scenario.scenario_json),
        "created_at": scenario.created_at.isoformat(),
        "label_tag": "SIMULATED SCENARIO — NOT ACTUAL FINANCIAL FORECAST",
    }


@router.post("/{scenario_id}/compare")
def compare_scenario_to_current(scenario_id: str, db: Session = Depends(get_db)) -> dict:
    """Re-runs the same scenario_type/params against the CURRENT live
    Financial Twin baseline, so the CFO can see whether a previously-run
    scenario's assumptions still hold given today's real numbers."""
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    current_inputs = gather_inputs(db)
    fresh_result = run_scenario(current_inputs, scenario.scenario_type, json.loads(scenario.input_json))

    return {
        "id": scenario.id,
        "original": {
            "baseline": json.loads(scenario.baseline_json),
            "scenario": json.loads(scenario.scenario_json),
            "created_at": scenario.created_at.isoformat(),
        },
        "current": fresh_result,
    }
