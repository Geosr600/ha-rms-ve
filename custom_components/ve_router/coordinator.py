from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VERouterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        api,
        scan_interval: int,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id if config_entry else 'default'}",
            update_interval=timedelta(seconds=scan_interval),
            config_entry=config_entry,
        )
        self.api = api
        self.config_entry = config_entry

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.api.get_data()
            params = await self.api.get_params()

            merged = dict(data)
            merged.update(params)

            try:
                energie = await self.api.get_energie()
                merged["energie_maxWh"] = energie.get("maxWh", 0)
                merged["energie_dateFin"] = energie.get("dateFin", 0)
                merged["energie_actif"] = energie.get("actif", False)
            except Exception as err:
                _LOGGER.debug("Unable to fetch /getEnergie: %s", err)

            return merged
        except Exception as err:
            raise UpdateFailed(f"Error communicating with VE router: {err}") from err
