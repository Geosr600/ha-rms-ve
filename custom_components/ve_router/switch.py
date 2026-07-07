from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .gpio_logic import async_sync_gpio14_for_intensity_source

from .const import (
    CONF_GPIO14_ACTION_NUMBER,
    CONF_GPIO5_ACTION_NUMBER,
    CONF_HC_ENABLED,
    CONF_SOC_LIMIT_ENABLED,
    DEFAULT_GPIO5_ACTION_NUMBER,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)

FORCE_OFF = 0


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    async_add_entities([
        VERouterForceActionSwitch(
            coordinator,
            api,
            entry,
            name="GPIO 14 - Utilisation I secondaire",
            unique_suffix="gpio14_secondary_current",
            action_key=CONF_GPIO14_ACTION_NUMBER,
            default_action=0,
            icon="mdi:electric-switch",
        ),
        VERouterForceActionSwitch(
            coordinator,
            api,
            entry,
            name="GPIO 5 - HC/HP",
            unique_suffix="gpio5_hchp",
            action_key=CONF_GPIO5_ACTION_NUMBER,
            default_action=0,
            icon="mdi:clock-outline",
        ),
        VERouterSocLimitSwitch(coordinator, api, entry),
        VERouterUseHcSwitch(coordinator, api, entry),
    ])


class VERouterForceActionSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(
        self,
        coordinator,
        api,
        entry: ConfigEntry,
        *,
        name: str,
        unique_suffix: str,
        action_key: str,
        default_action: int,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_icon = icon
        self._action_key = action_key
        self._num_action = int(entry.data.get(action_key, default_action))
        self._fallback_state: bool | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def is_on(self) -> bool | None:
        actions = (self.coordinator.data or {}).get("actions", {})
        action = actions.get(self._num_action)
        if action is None:
            return self._fallback_state

        force = int(action.get("force", 0) or 0)
        real_state = action.get("is_on")

        if force > 0:
            return True
        if force == 0 and real_state is not None:
            return bool(real_state)
        return self._fallback_state

    async def async_turn_on(self, **kwargs) -> None:
        await self._api.force_action(self._num_action, 1440)
        if self._action_key == CONF_GPIO5_ACTION_NUMBER:
            await async_sync_gpio14_for_intensity_source(
                self.coordinator,
                self._api,
                self._entry,
                hchp_target_on=True,
            )
        self._fallback_state = True
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._api.force_action(self._num_action, FORCE_OFF)
        if self._action_key == CONF_GPIO5_ACTION_NUMBER:
            await async_sync_gpio14_for_intensity_source(
                self.coordinator,
                self._api,
                self._entry,
                hchp_target_on=False,
            )
        self._fallback_state = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class VERouterSocLimitSwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "Utiliser SOC véhicule cible"
    _attr_unique_id_suffix = "soc_limit_enabled"
    _attr_icon = "mdi:battery-sync"

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self._attr_unique_id_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def is_on(self) -> bool:
        return bool(self._entry.options.get(CONF_SOC_LIMIT_ENABLED, False))

    async def async_turn_on(self, **kwargs) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_SOC_LIMIT_ENABLED: True,
            },
        )
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_SOC_LIMIT_ENABLED: False,
            },
        )
        self.async_write_ha_state()



class VERouterUseHcSwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "Utiliser HC"
    _attr_unique_id_suffix = "hc_enabled"
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self._attr_unique_id_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def is_on(self) -> bool:
        return bool(self._entry.options.get(CONF_HC_ENABLED, False))

    async def async_turn_on(self, **kwargs) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, CONF_HC_ENABLED: True},
        )
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, CONF_HC_ENABLED: False},
        )
        if DOMAIN in self.hass.data and self._entry.entry_id in self.hass.data[DOMAIN]:
            entry_state = self.hass.data[DOMAIN][self._entry.entry_id]
            entry_state["hc_window_active"] = False
            entry_state["hc_charge_launched"] = False
            entry_state["last_hc_trigger_key"] = None

        # Sécurité : désactiver HC doit aussi couper immédiatement l'action HC côté routeur.
        # Sans ça, GPIO5 peut rester forcé ON jusqu'à la fin de la durée précédente.
        num_gpio5 = int(
            self._entry.data.get(CONF_GPIO5_ACTION_NUMBER, DEFAULT_GPIO5_ACTION_NUMBER) or 0
        )
        if num_gpio5 > 0:
            await self._api.force_action(num_gpio5, FORCE_OFF)

        # Si HC/HP utilisait l'intensité secondaire, GPIO14 peut avoir été activé.
        # On resynchronise avec HC explicitement OFF pour éviter un état fantôme.
        await async_sync_gpio14_for_intensity_source(
            self.coordinator,
            self._api,
            self._entry,
            hchp_target_on=False,
        )

        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
