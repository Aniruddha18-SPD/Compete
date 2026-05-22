from pydantic import BaseModel
from typing import Optional
import json


class Query(BaseModel):
    id: str
    query_text: str
    intent: str
    domain: str
    query_attrs: dict = {}
    persona_context: Optional[str] = None
    created_at: Optional[str] = None


class Assertion(BaseModel):
    id: str
    query_id: str
    assertion_text: str
    level: str
    dimension: str


class Run(BaseModel):
    id: str
    run_name: Optional[str] = None
    query_set_version: str = "v1"
    status: str = "pending"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class Response(BaseModel):
    id: str
    run_id: str
    query_id: str
    product: str
    response_text: str
    response_metadata: dict = {}
    captured_at: Optional[str] = None
    capture_method: str = "mock"


class Verdict(BaseModel):
    id: str
    response_id: str
    assertion_id: str
    passed: bool
    judge_reasoning: Optional[str] = None
    judge_confidence: Optional[float] = None
    judged_at: Optional[str] = None


class PairResult(BaseModel):
    id: str
    run_id: str
    query_id: str
    mindtrip_pass_rate: float
    wanderboat_pass_rate: float
    outcome: str
    outcome_severity: str = "critical"


def row_to_dict(row) -> dict:
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, (dict, list)):
                    d[k] = parsed
            except (json.JSONDecodeError, ValueError):
                pass
    return d
