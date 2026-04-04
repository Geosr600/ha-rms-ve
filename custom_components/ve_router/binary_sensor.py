from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        VERouterAutoRegulationAvailableBinarySensor(coordinator, entry),
        VERouterInternalHCBinarySensor(coordinator, entry),
    ])


class _BaseBinary(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, name, unique, key, icon, enabled=True, diagnostic=False):
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique}"
        self._attr_icon = icon
        self._attr_entity_registry_enabled_default = enabled
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        return int(self.coordinator.data.get(self._key, 0)) == 1

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )


class VERouterAutoRegulationAvailableBinarySensor(_BaseBinary):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Régulation auto VE disponible", "enab", "enab", "mdi:auto-mode", True, False)


class VERouterInternalHCBinarySensor(_BaseBinary):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "Heures creuses internes VE actives", "enabIntHC", "enabIntHC", "mdi:clock-check-outline", False, True)
