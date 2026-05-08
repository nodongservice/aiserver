from typing import Any

from pydantic import BaseModel

SUCCESS_CODE = "SUCCESS"
SUCCESS_MESSAGE = "성공"


def to_plain_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, tuple):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}
    return value


def success_response(result: Any, message: str = SUCCESS_MESSAGE) -> dict[str, Any]:
    return {
        "code": SUCCESS_CODE,
        "message": message,
        "result": to_plain_data(result),
    }
