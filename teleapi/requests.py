from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import aiohttp

from common import log


@dataclass
class RequestResponse:
    message_id: Optional[str] = None
    status: int = 504
    content: Optional[bytes] = None
    error: Optional[str] = None
    json: Dict[str, Any] = field(default_factory=dict)


async def request(
    session: aiohttp.ClientSession,
    url,
    method="GET",
    files: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> RequestResponse:
    if files:
        form = aiohttp.FormData()
        for key, file_obj in files.items():
            form.add_field(key, file_obj, filename=getattr(file_obj, "name", key))
        kwargs["data"] = form

    try:
        async with session.request(method, url, **kwargs) as response:
            content_type = response.headers.get("Content-Type", "")

            json_body: Dict[str, Any] = {}
            if "application/json" in content_type:
                parsed = await response.json()
                if isinstance(parsed, dict):
                    json_body = parsed

            content = await response.read()

            return RequestResponse(
                status=response.status,
                json=json_body,
                content=content,
            )

    except Exception as e:
        log.logger.warning(f"[API] {type(e).__name__} - {repr(e)}")
        return RequestResponse(
            status=getattr(e, "status", 504) or 504,
            error=f"{type(e).__name__} - {repr(e)}",
            json={},
        )

    finally:
        if files:
            for file_obj in files.values():
                try:
                    file_obj.close()
                except Exception:
                    pass
