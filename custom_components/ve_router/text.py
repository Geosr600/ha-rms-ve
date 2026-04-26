from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import (
    CONF_VEHICLE_SOC_ENTITY,
    DEFAULT_VEHICLE_SOC_ENTITY,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([VERouterVehicleSocEntityText(entry)])


class VERouterVehicleSocEntityText(TextEntity):
    _attr_name = "Entité SOC véhicule"
    _attr_icon = "mdi:car-electric"
    _attr_mode = TextMode.TEXT
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_vehicle_soc_entity"

    @property
    def native_value(self) -> str:
        return str(self._entry.options.get(CONF_VEHICLE_SOC_ENTITY, DEFAULT_VEHICLE_SOC_ENTITY) or "")

    async def async_set_value(self, value: str) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_VEHICLE_SOC_ENTITY: str(value or "").strip(),
            },
        )
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
