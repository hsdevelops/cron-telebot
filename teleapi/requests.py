from typing import Any, Dict, Optional, TypedDict
import aiohttp

from common import log


class RequestResponse(TypedDict):
    message_id: Optional[str]
    status: int
    content: Optional[bytes]
    error: Optional[str]


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

            json_body = None
            if "application/json" in content_type:
                json_body = await response.json()

            content = await response.read()

            return {
                "status": response.status,
                "json": json_body,
                "content": content,
            }

    except aiohttp.ClientResponseError as e:
        log.logger.warning(f"[API] status = {e.status}, {type(e).__name__} - {repr(e)}")
        return {
            "status": e.status,
            "error": str(e),
        }

    except aiohttp.ClientError as e:
        log.logger.warning(f"[API] {type(e).__name__} - {repr(e)}")
        return {
            "status": None,
            "error": str(e),
        }
