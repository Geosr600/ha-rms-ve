from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VERouterApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VERouterCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        api: VERouterApi,
        scan_interval: int,
        config_entry=None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
            config_entry=config_entry,
        )
        self.api = api

    async def _async_update_data(self):
        try:
            return await self.api.get_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with VE router: {err}") from err
