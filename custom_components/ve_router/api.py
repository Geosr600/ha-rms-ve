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

    async def set_gpio(self, gpio: int, out: bool | int) -> None:
        value = 1 if bool(out) else 0
        async with self._session.get(
            f"{self.base_url}/SetGPIO?gpio={int(gpio)}&out={value}",
            timeout=10,
        ) as resp:
            resp.raise_for_status()
            await resp.text()

    async def force_action(self, num_action: int, force: int) -> None:
        async with self._session.get(
            f"{self.base_url}/ForceAction?Force={int(force)}&NumAction={int(num_action)}",
            timeout=10,
        ) as resp:
            resp.raise_for_status()
            await resp.text()

    async def get_actions(self) -> dict[str, Any]:
        async with self._session.get(f"{self.base_url}/ajax_etatActions", timeout=10) as resp:
            resp.raise_for_status()
            text = await resp.text()
        return self._parse_actions_payload(text)


    
    @staticmethod
    def _parse_actions_payload(text: str) -> dict[str, Any]:
        gs = chr(29)
        rs = chr(30)
        groups = text.split(gs)
        actions: dict[int, dict[str, Any]] = {}

        for group in groups[4:]:
            if not group:
                continue
            fields = group.split(rs)
            if len(fields) < 5:
                continue
            try:
                num_action = int(fields[0])
            except (TypeError, ValueError):
                continue

            raw_state = fields[2].strip()
            state_lower = raw_state.lower()
            if state_lower == "on":
                is_on = True
            elif state_lower == "off":
                is_on = False
            else:
                try:
                    is_on = int(float(raw_state)) > 0
                except (TypeError, ValueError):
                    is_on = None

            try:
                force = int(float(fields[3]))
            except (TypeError, ValueError):
                force = 0

            try:
                hequiv = int(float(fields[4]))
            except (TypeError, ValueError):
                hequiv = 0

            actions[num_action] = {
                "num_action": num_action,
                "title": fields[1],
                "raw_state": raw_state,
                "is_on": is_on,
                "force": force,
                "hequiv": hequiv,
            }

        return {"actions": actions}

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
