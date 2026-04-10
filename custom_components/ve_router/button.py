from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    MODE_ARRET,
    MODE_AUTO,
    MODE_MANUEL,
    MODE_SEMI_AUTO,
)


@dataclass(frozen=True, kw_only=True)
class VERouterButtonDescription(ButtonEntityDescription):
    mode: int | None = None
    refresh_only: bool = False
    entity_category: EntityCategory | None = None


BUTTONS: tuple[VERouterButtonDescription, ...] = (
    VERouterButtonDescription(
        key="mode_auto",
        name="Mode Auto",
        icon="mdi:auto-mode",
        mode=MODE_AUTO,
    ),
    VERouterButtonDescription(
        key="mode_semi_auto",
        name="Mode Semi-auto",
        icon="mdi:car-electric",
        mode=MODE_SEMI_AUTO,
    ),
    VERouterButtonDescription(
        key="mode_manuel",
        name="Mode Manuel",
        icon="mdi:hand-back-right",
        mode=MODE_MANUEL,
    ),
    VERouterButtonDescription(
        key="mode_arret",
        name="Mode Arrêt",
        icon="mdi:stop-circle-outline",
        mode=MODE_ARRET,
    ),
    VERouterButtonDescription(
        key="refresh",
        name="Rafraîchir",
        icon="mdi:refresh",
        refresh_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VERouterButton(data["coordinator"], data["api"], entry, description)
        for description in BUTTONS
    )


class VERouterButton(CoordinatorEntity, ButtonEntity):
    entity_description: VERouterButtonDescription

    def __init__(self, coordinator, api, entry: ConfigEntry, description: VERouterButtonDescription) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    async def async_press(self) -> None:
        if self.entity_description.refresh_only:
            await self.coordinator.async_request_refresh()
            return

        await self._api.set_mode(self.entity_description.mode)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
