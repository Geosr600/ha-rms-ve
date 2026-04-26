from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .gpio_logic import async_sync_gpio14_for_intensity_source

from .const import (
    CONF_ON_PLUG_ACTION,
    CONF_ON_UNPLUG_ACTION,
    CONF_HCHP_INTENSITY_SOURCE,
    CONF_MANUAL_INTENSITY_SOURCE,
    DEFAULT_INTENSITY_SOURCE,
    DEFAULT_ON_PLUG_ACTION,
    DEFAULT_ON_UNPLUG_ACTION,
    DOMAIN,
    INTENSITY_SOURCE_BY_LABEL,
    INTENSITY_SOURCE_LABELS,
    MANUFACTURER,
    MODEL,
    MODE_BY_LABEL,
    MODE_MANUEL,
    MODE_LABELS,
    PLUG_ACTIONS,
)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            VERouterModeSelect(data["coordinator"], data["api"], entry),
            VERouterOnPlugActionSelect(entry),
            VERouterOnUnplugActionSelect(entry),
            VERouterManualIntensitySourceSelect(entry),
            VERouterHchpIntensitySourceSelect(entry),
        ]
    )


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
        mode = MODE_BY_LABEL[option]
        await self._api.set_mode(mode)
        await async_sync_gpio14_for_intensity_source(
            self.coordinator,
            self._api,
            self._entry,
            target_mode=mode,
        )
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )


class _BaseActionSelect(SelectEntity, RestoreEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _option_key = ""
    _default_option = DEFAULT_ON_PLUG_ACTION

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_options = list(PLUG_ACTIONS.values())

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if (
            last_state is not None
            and self._entry.options.get(self._option_key) is None
            and last_state.state in self._attr_options
        ):
            action_key = next(
                (key for key, label in PLUG_ACTIONS.items() if label == last_state.state),
                None,
            )
            if action_key is not None:
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    options={
                        **self._entry.options,
                        self._option_key: action_key,
                    },
                )

    @property
    def current_option(self):
        action = self._entry.options.get(self._option_key, self._default_option)
        return PLUG_ACTIONS.get(action, PLUG_ACTIONS[self._default_option])

    async def async_select_option(self, option: str) -> None:
        action_key = next((key for key, label in PLUG_ACTIONS.items() if label == option), None)
        if action_key is None:
            return

        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                self._option_key: action_key,
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


class VERouterOnPlugActionSelect(_BaseActionSelect):
    _attr_name = "Action au branchement"
    _attr_icon = "mdi:ev-station"
    _option_key = CONF_ON_PLUG_ACTION
    _default_option = DEFAULT_ON_PLUG_ACTION

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_on_plug_action_select"


class VERouterOnUnplugActionSelect(_BaseActionSelect):
    _attr_name = "Action au débranchement"
    _attr_icon = "mdi:power-plug-off"
    _option_key = CONF_ON_UNPLUG_ACTION
    _default_option = DEFAULT_ON_UNPLUG_ACTION

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_on_unplug_action_select"


class _BaseIntensitySourceSelect(SelectEntity, RestoreEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _option_key = ""
    _default_option = DEFAULT_INTENSITY_SOURCE

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_options = list(INTENSITY_SOURCE_BY_LABEL.keys())

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if (
            last_state is not None
            and self._entry.options.get(self._option_key) is None
            and last_state.state in self._attr_options
        ):
            source_key = INTENSITY_SOURCE_BY_LABEL.get(last_state.state)
            if source_key is not None:
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    options={
                        **self._entry.options,
                        self._option_key: source_key,
                    },
                )

    @property
    def current_option(self):
        source = self._entry.options.get(self._option_key, self._default_option)
        return INTENSITY_SOURCE_LABELS.get(source, INTENSITY_SOURCE_LABELS[self._default_option])

    async def async_select_option(self, option: str) -> None:
        source_key = INTENSITY_SOURCE_BY_LABEL.get(option)
        if source_key is None:
            return
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                self._option_key: source_key,
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


class VERouterManualIntensitySourceSelect(_BaseIntensitySourceSelect):
    _attr_name = "Mode Manuel - source intensité"
    _attr_icon = "mdi:current-ac"
    _option_key = CONF_MANUAL_INTENSITY_SOURCE

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_intensity_source"


class VERouterHchpIntensitySourceSelect(_BaseIntensitySourceSelect):
    _attr_name = "HC/HP - source intensité"
    _attr_icon = "mdi:current-ac"
    _option_key = CONF_HCHP_INTENSITY_SOURCE

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_hchp_intensity_source"
