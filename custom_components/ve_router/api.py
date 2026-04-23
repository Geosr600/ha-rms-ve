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
                raise ValueError("Invalid JSON payload from /data")
            return data

    async def get_params(self) -> dict[str, Any]:
        async with self._session.get(f"{self.base_url}/getParams", timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON payload from /getParams")
            return data

    async def save_params(self, params: dict[str, Any]) -> None:
        async with self._session.post(
            f"{self.base_url}/saveParams",
            json=params,
            timeout=10,
        ) as resp:
            resp.raise_for_status()
            await resp.text()

    async def get_energie(self) -> dict[str, Any]:
        async with self._session.get(f"{self.base_url}/getEnergie", timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON payload from /getEnergie")
            return data

    async def set_energie(self, max_wh: int, date_fin: int) -> None:
        async with self._session.get(
            f"{self.base_url}/setEnergie?maxWh={int(max_wh)}&dateFin={int(date_fin)}",
            timeout=10,
        ) as resp:
            resp.raise_for_status()
            await resp.text()

    async def set_mode(self, mode: int) -> None:
        async with self._session.get(f"{self.base_url}/setMode?mode={mode}", timeout=10) as resp:
            resp.raise_for_status()
            await resp.text()

    async def set_current(self, amp: float) -> None:
        async with self._session.get(f"{self.base_url}/setCurrent?amp={amp}", timeout=10) as resp:
            resp.raise_for_status()
            await resp.text()

    async def async_test_connection(self) -> dict[str, Any]:
        data = await self.get_data()
        params = await self.get_params()

        merged: dict[str, Any] = {}
        merged.update(data)
        merged.update(params)

        try:
            energie = await self.get_energie()
            merged["energie_maxWh"] = energie.get("maxWh", 0)
            merged["energie_dateFin"] = energie.get("dateFin", 0)
            merged["energie_actif"] = energie.get("actif", False)
        except Exception:
            pass

        return merged
