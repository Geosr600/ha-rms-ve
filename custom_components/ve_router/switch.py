from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .gpio_logic import async_sync_gpio14_for_intensity_source

from .const import (
    CONF_GPIO14_ACTION_NUMBER,
    CONF_GPIO14_FORCE_VALUE,
    CONF_GPIO5_ACTION_NUMBER,
    CONF_GPIO5_FORCE_VALUE,
    CONF_HC_ENABLED,
    CONF_SOC_LIMIT_ENABLED,
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
            force_key=CONF_GPIO14_FORCE_VALUE,
            default_action=0,
            default_force=1440,
            icon="mdi:electric-switch",
        ),
        VERouterForceActionSwitch(
            coordinator,
            api,
            entry,
            name="GPIO 5 - HC/HP",
            unique_suffix="gpio5_hchp",
            action_key=CONF_GPIO5_ACTION_NUMBER,
            force_key=CONF_GPIO5_FORCE_VALUE,
            default_action=0,
            default_force=1440,
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
        force_key: str,
        default_action: int,
        default_force: int,
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
        self._force_key = force_key
        self._default_force = default_force
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
        force_on = int(self._entry.data.get(self._force_key, self._default_force))
        await self._api.force_action(self._num_action, force_on)
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
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
