"""Gọi Claude và ép kết quả về đúng schema Pydantic (qua tool use bắt buộc)."""
import base64
from typing import List, Optional, Type, TypeVar

from pydantic import BaseModel

from . import config

T = TypeVar("T", bound=BaseModel)


def ask_structured(system: str, prompt: str, schema: Type[T], max_tokens: int = 8000,
                   images: Optional[List[bytes]] = None, model: str = "") -> tuple:
    """Trả về (đối tượng đã validate, usage để tính chi phí).
    images: danh sách ảnh JPEG (bytes) gửi kèm cho các agent cần "nhìn" (QA video)."""
    import anthropic

    model = model or config.CLAUDE_MODEL
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=3)
    tool = {
        "name": "submit_result",
        "description": "Nộp kết quả cuối cùng, đúng schema.",
        "input_schema": schema.model_json_schema(),
    }
    content: list = []
    for img in images or []:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(img).decode()}})
    content.append({"type": "text", "text": prompt})

    last_err = None
    for _ in range(2):  # thử lại 1 lần nếu JSON sai schema
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_result"},
            messages=[{"role": "user", "content": content}],
        )
        usage = {"model": model,
                 "input_tokens": msg.usage.input_tokens,
                 "output_tokens": msg.usage.output_tokens}
        for block in msg.content:
            if block.type == "tool_use":
                try:
                    return schema.model_validate(block.input), usage
                except Exception as e:  # noqa: BLE001
                    last_err = e
    raise RuntimeError(f"Claude không trả về đúng schema: {last_err}")
