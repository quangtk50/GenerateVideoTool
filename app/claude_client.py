"""Gọi Claude và ép kết quả về đúng schema Pydantic (qua tool use bắt buộc)."""
from typing import Type, TypeVar

from pydantic import BaseModel

from . import config

T = TypeVar("T", bound=BaseModel)


def ask_structured(system: str, prompt: str, schema: Type[T], max_tokens: int = 8000) -> tuple[T, dict]:
    """Trả về (đối tượng đã validate, thông tin usage để tính chi phí)."""
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    tool = {
        "name": "submit_result",
        "description": "Nộp kết quả cuối cùng, đúng schema.",
        "input_schema": schema.model_json_schema(),
    }
    last_err = None
    for _ in range(2):  # thử lại 1 lần nếu JSON sai schema
        msg = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_result"},
            messages=[{"role": "user", "content": prompt}],
        )
        usage = {"model": config.CLAUDE_MODEL,
                 "input_tokens": msg.usage.input_tokens,
                 "output_tokens": msg.usage.output_tokens}
        for block in msg.content:
            if block.type == "tool_use":
                try:
                    return schema.model_validate(block.input), usage
                except Exception as e:  # noqa: BLE001
                    last_err = e
    raise RuntimeError(f"Claude không trả về đúng schema: {last_err}")
