import aiohttp
from typing import Any, Dict

DPS_REPORT_BASE = "https://dps.report"


async def upload_to_dps_report(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Upload an ArcDPS log to dps.report and return the JSON response.
    """
    url = f"{DPS_REPORT_BASE}/uploadContent?json=1"
    data = aiohttp.FormData()
    data.add_field(
        "file",
        file_bytes,
        filename=filename,
        content_type="application/octet-stream",
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            resp.raise_for_status()
            return await resp.json()


async def fetch_ei_json(report_id_or_permalink: str) -> Dict[str, Any]:
    """
    Fetch Elite Insights JSON from dps.report for a given report id or permalink.

    We first try using `id=`, and if that returns HTTP 403,
    we retry using `permalink=`.
    """
    async with aiohttp.ClientSession() as session:
        # 1) Try id=
        try:
            async with session.get(
                f"{DPS_REPORT_BASE}/getJson",
                params={"id": report_id_or_permalink},
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 403:
                # 2) Try permalink=
                async with session.get(
                    f"{DPS_REPORT_BASE}/getJson",
                    params={"permalink": report_id_or_permalink},
                ) as resp2:
                    resp2.raise_for_status()
                    return await resp2.json()
            # Re-raise so caller can handle status codes
            raise


async def fetch_upload_metadata(report_id: str) -> Dict[str, Any]:
    """
    Fetch upload metadata (encounter info, including jsonAvailable)
    for an existing dps.report id.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{DPS_REPORT_BASE}/getUploadMetadata",
            params={"json": 1, "id": report_id},
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
