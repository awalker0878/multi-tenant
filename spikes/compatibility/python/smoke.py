"""Probe installed validation and HTTP libraries without a service or network call."""

import json
from importlib.metadata import version
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError


class ProbeMessage(BaseModel):
    """Synthetic library input, deliberately not a product contract."""

    model_config = ConfigDict(extra="forbid", strict=True)
    sample_id: UUID
    revision: int


def main() -> None:
    payload = '{"sample_id":"00000000-0000-4000-8000-000000000001","revision":1}'
    item = ProbeMessage.model_validate_json(payload)
    assert item.revision == 1
    assert ProbeMessage.model_validate_json(item.model_dump_json()) == item
    for invalid in (
        '{"sample_id":"invalid","revision":1}',
        payload.replace('"revision":1', '"revision":"1"'),
        payload.replace('"revision":1', '"revision":1,"unexpected":true'),
    ):
        try:
            ProbeMessage.model_validate_json(invalid)
        except ValidationError:
            pass
        else:
            raise AssertionError("Invalid probe input was accepted")

    def echo(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "compatibility.invalid"
        return httpx.Response(200, content=request.content, headers={"content-type": "application/json"})

    with httpx.Client(transport=httpx.MockTransport(echo), timeout=1.0) as client:
        response = client.post("https://compatibility.invalid/probe", content=item.model_dump_json())
        response.raise_for_status()
        assert ProbeMessage.model_validate_json(response.content) == item
    print(json.dumps({"result": "PASS", "checks": 5, "pydantic": version("pydantic"), "httpx": version("httpx"), "network": "MockTransport only"}))


if __name__ == "__main__":
    main()
