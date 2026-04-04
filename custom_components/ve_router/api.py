from __future__ import annotations

from typing import Any
from aiohttp import ClientSession


class VERouterApi:
    def __init__(self, session: ClientSession, host: str) -> None:
        self._session = session
        self._host = host.rstrip("/")

    @property
    def base_url(self) -> str:
        return f"http://{self._host}"

    async def get_data(self) -> dict[str, Any]:
        async with self._session.get(f"{self.base_url}/data", timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON payload")
            return data

    async def set_mode(self, mode: int) -> None:
        async with self._session.get(f"{self.base_url}/setMode?mode={mode}", timeout=10) as resp:
            resp.raise_for_status()
            await resp.text()

    async def set_current(self, amp: int) -> None:
        async with self._session.get(f"{self.base_url}/setCurrent?amp={amp}", timeout=10) as resp:
            resp.raise_for_status()
            await resp.text()

    async def async_test_connection(self) -> dict[str, Any]:
        return await self.get_data()
