from typing import Any, Dict, Optional
import aiohttp


async def request(
    session: aiohttp.ClientSession,
    url,
    method="GET",
    files: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict:

    if files:
        form = aiohttp.FormData()
        for key, file_obj in files.items():
            form.add_field(key, file_obj, filename=getattr(file_obj, "name", key))
        kwargs["data"] = form

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
