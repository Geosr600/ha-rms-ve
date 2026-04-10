from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER, MODEL


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VERouterEnergyEndDateTime(data["coordinator"], data["api"], entry)])


class VERouterEnergyEndDateTime(CoordinatorEntity, DateTimeEntity):
    _attr_name = "Date de fin"
    _attr_icon = "mdi:calendar-end"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_energie_datefin"

    @property
    def native_value(self) -> datetime | None:
        timestamp_ms = int(self.coordinator.data.get("energie_dateFin", 0) or 0)
        if timestamp_ms <= 0:
            return None
        value_utc = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        return dt_util.as_local(value_utc)

    async def async_set_value(self, value: datetime) -> None:
        local_value = value
        if local_value.tzinfo is None:
            local_value = dt_util.as_local(local_value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))
        timestamp_ms = int(local_value.timestamp() * 1000)
        max_wh = int(self.coordinator.data.get("energie_maxWh", 0) or 0)
        await self._api.set_energie(max_wh, timestamp_ms)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
