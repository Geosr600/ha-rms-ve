from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VERouterManualCurrentNumber(data["coordinator"], data["api"], entry)])


class VERouterManualCurrentNumber(CoordinatorEntity, NumberEntity):
    _attr_name = "I charge manual"
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_manual_current"

    @property
    def native_min_value(self) -> float:
        return float(self.coordinator.data.get("I_min_c", 6) or 6)

    @property
    def native_max_value(self) -> float:
        value = float(self.coordinator.data.get("I_max", 32) or 32)
        min_value = self.native_min_value
        return value if value >= min_value else min_value

    @property
    def native_value(self):
        value = float(self.coordinator.data.get("I_charge_manual", self.native_min_value))
        return min(max(value, self.native_min_value), self.native_max_value)

    async def async_set_native_value(self, value: float) -> None:
        await self._api.set_current(int(value))
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
