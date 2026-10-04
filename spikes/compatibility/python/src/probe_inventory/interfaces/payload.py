"""Transport validation stays at the boundary in this synthetic fixture."""

from pydantic import BaseModel, ConfigDict


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    label: str


def parse_label(payload: str) -> str:
    return Payload.model_validate_json(payload).label
