from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL, MODE_BY_LABEL, MODE_LABELS


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VERouterModeSelect(data["coordinator"], data["api"], entry)])


class VERouterModeSelect(CoordinatorEntity, SelectEntity):
    _attr_name = "Mode de fonctionnement"
    _attr_icon = "mdi:cog"

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_mode_select"
        self._attr_options = list(MODE_BY_LABEL.keys())

    @property
    def current_option(self):
        return MODE_LABELS.get(self.coordinator.data.get("mode"), self._attr_options[0])

    async def async_select_option(self, option: str) -> None:
        await self._api.set_mode(MODE_BY_LABEL[option])
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
