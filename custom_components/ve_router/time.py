from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HC_START_TIME,
    DEFAULT_HC_START_TIME,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    async_add_entities([VERouterHcStartTime(coordinator, api, entry)])


class VERouterHcStartTime(CoordinatorEntity, TimeEntity):
    _attr_name = "Heure creuse"
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_hc_start_time"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def native_value(self) -> time | None:
        value = str(self._entry.options.get(CONF_HC_START_TIME, DEFAULT_HC_START_TIME) or DEFAULT_HC_START_TIME)
        try:
            hour, minute = value[:5].split(":")
            return time(hour=int(hour), minute=int(minute))
        except (TypeError, ValueError):
            return time(hour=22, minute=0)

    async def async_set_value(self, value: time) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, CONF_HC_START_TIME: value.strftime("%H:%M")},
        )
        self.async_write_ha_state()
