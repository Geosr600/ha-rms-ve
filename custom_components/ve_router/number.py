from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_GPIO14_FORCE_VALUE,
    CONF_GPIO5_FORCE_VALUE,
    CONF_TARGET_SOC,
    DEFAULT_TARGET_SOC,
    MIN_TARGET_SOC,
    MAX_TARGET_SOC,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)


PARAMS: dict[str, dict[str, Any]] = {
    "I_min_c": {
        "name": "Courant charge min",
        "min": 1,
        "max": 32,
        "step": 1,
        "unit": "A",
        "icon": "mdi:current-ac",
        "cast": "float",
    },
    "I_max": {
        "name": "Courant charge max",
        "min": 1,
        "max": 32,
        "step": 1,
        "unit": "A",
        "icon": "mdi:current-ac",
        "cast": "float",
    },
    "I_min_c1": {
        "name": "Courant charge min 2",
        "min": 1,
        "max": 32,
        "step": 1,
        "unit": "A",
        "icon": "mdi:current-ac",
        "cast": "float",
    },
    "I_max1": {
        "name": "Courant charge max 2",
        "min": 1,
        "max": 32,
        "step": 1,
        "unit": "A",
        "icon": "mdi:current-ac",
        "cast": "float",
    },
    "U_reseau": {
        "name": "Tension réseau",
        "min": 180,
        "max": 260,
        "step": 1,
        "unit": "V",
        "icon": "mdi:sine-wave",
        "cast": "float",
    },
    "P_charge_min": {
        "name": "P charge min",
        "min": 0,
        "max": 10000,
        "step": 10,
        "unit": "W",
        "icon": "mdi:flash",
        "cast": "float",
    },
    "P_charge_max": {
        "name": "P charge max",
        "min": -5000,
        "max": 5000,
        "step": 10,
        "unit": "W",
        "icon": "mdi:flash-alert",
        "cast": "float",
    },
    "t_depassement": {
        "name": "Temps dépassement",
        "min": 0,
        "max": 120,
        "step": 1,
        "unit": "s",
        "icon": "mdi:timer-outline",
        "cast": "int",
    },
    "PAbonneReseau": {
        "name": "P abonnement réseau",
        "min": 0,
        "max": 36000,
        "step": 100,
        "unit": "W",
        "icon": "mdi:home-lightning-bolt",
        "cast": "float",
    },
    "t_delay_boucle": {
        "name": "Temps d'attente entre traitements",
        "min": 0,
        "max": 10000,
        "step": 10,
        "unit": "ms",
        "icon": "mdi:timer-cog-outline",
        "cast": "int",
    },
    "P_seuil_regul": {
        "name": "Seuil de régulation",
        "min": -10000,
        "max": 10000,
        "step": 10,
        "unit": "W",
        "icon": "mdi:tune",
        "cast": "float",
    },
    "I_charge_manual1": {
        "name": "I charge manual 2",
        "min": 1,
        "max": 32,
        "step": 1,
        "unit": "A",
        "icon": "mdi:lightning-bolt",
        "cast": "float",
    },
}


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities: list[NumberEntity] = [
        VERouterManualCurrentNumber(coordinator, api, entry),
        VERouterEnergyWhNumber(coordinator, api, entry),
        VERouterTargetSocNumber(coordinator, api, entry),
        VERouterForceDurationNumber(
            coordinator,
            api,
            entry,
            name="GPIO 14 - Durée forçage ON",
            unique_suffix="gpio14_force_value",
            config_key=CONF_GPIO14_FORCE_VALUE,
            default_value=1440,
        ),
        VERouterForceDurationNumber(
            coordinator,
            api,
            entry,
            name="GPIO 5 - Durée forçage ON",
            unique_suffix="gpio5_force_value",
            config_key=CONF_GPIO5_FORCE_VALUE,
            default_value=1440,
        ),
    ]

    for param_key in PARAMS:
        entities.append(VERouterParamNumber(coordinator, api, entry, param_key))

    async_add_entities(entities)


class VERouterBaseNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )


class VERouterManualCurrentNumber(VERouterBaseNumber):
    _attr_name = "I charge manual"
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator, api, entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_current"

    @property
    def native_min_value(self) -> float:
        return float(self.coordinator.data.get("I_min_c", 1) or 1)

    @property
    def native_max_value(self) -> float:
        value = float(self.coordinator.data.get("I_max", 32) or 32)
        min_value = self.native_min_value
        return value if value >= min_value else min_value

    @property
    def native_value(self) -> float:
        value = float(self.coordinator.data.get("I_charge_manual", self.native_min_value))
        return min(max(value, self.native_min_value), self.native_max_value)

    async def async_set_native_value(self, value: float) -> None:
        await self._api.set_current(float(value))
        await self.coordinator.async_request_refresh()



class VERouterTargetSocNumber(VERouterBaseNumber):
    _attr_mode = NumberMode.SLIDER
    _attr_name = "SOC véhicule cible"
    _attr_native_unit_of_measurement = "%"
    _attr_native_step = 1
    _attr_icon = "mdi:battery-check"

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator, api, entry)
        self._attr_unique_id = f"{entry.entry_id}_target_soc"

    @property
    def native_min_value(self) -> float:
        return float(MIN_TARGET_SOC)

    @property
    def native_max_value(self) -> float:
        return float(MAX_TARGET_SOC)

    @property
    def native_value(self) -> float:
        return float(self._entry.options.get(CONF_TARGET_SOC, DEFAULT_TARGET_SOC))

    async def async_set_native_value(self, value: float) -> None:
        target = int(max(MIN_TARGET_SOC, min(MAX_TARGET_SOC, round(value))))
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_TARGET_SOC: target,
            },
        )
        self.async_write_ha_state()


class VERouterEnergyWhNumber(VERouterBaseNumber):
    _attr_mode = NumberMode.BOX
    _attr_name = "Wh à ajouter"
    _attr_native_unit_of_measurement = "Wh"
    _attr_native_step = 100
    _attr_icon = "mdi:battery-plus"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator, api, entry)
        self._attr_unique_id = f"{entry.entry_id}_energie_maxwh"

    @property
    def native_min_value(self) -> float:
        return 0.0

    @property
    def native_max_value(self) -> float:
        return 50000.0

    @property
    def native_value(self) -> float:
        return float(self.coordinator.data.get("energie_maxWh", 0) or 0)

    async def async_set_native_value(self, value: float) -> None:
        date_fin = int(self.coordinator.data.get("energie_dateFin", 0) or 0)
        await self._api.set_energie(int(value), date_fin)
        await self.coordinator.async_request_refresh()

class VERouterForceDurationNumber(VERouterBaseNumber):
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "min"
    _attr_native_step = 1
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(
        self,
        coordinator,
        api,
        entry: ConfigEntry,
        *,
        name: str,
        unique_suffix: str,
        config_key: str,
        default_value: int,
    ) -> None:
        super().__init__(coordinator, api, entry)
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._config_key = config_key
        self._default_value = default_value

    @property
    def native_min_value(self) -> float:
        return 0.0

    @property
    def native_max_value(self) -> float:
        return 10080.0

    @property
    def native_value(self) -> float:
        return float(self._entry.data.get(self._config_key, self._default_value))

    async def async_set_native_value(self, value: float) -> None:
        new_data = dict(self._entry.data)
        new_data[self._config_key] = int(value)
        self.hass.config_entries.async_update_entry(self._entry, data=new_data)
        self.async_write_ha_state()


class VERouterParamNumber(VERouterBaseNumber):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, api, entry: ConfigEntry, param_key: str) -> None:
        super().__init__(coordinator, api, entry)
        cfg = PARAMS[param_key]

        self._param_key = param_key
        self._cast = cfg["cast"]
        self._min = cfg["min"]
        self._max = cfg["max"]

        self._attr_name = cfg["name"]
        self._attr_unique_id = f"{entry.entry_id}_{param_key}"
        self._attr_native_step = cfg["step"]
        self._attr_native_unit_of_measurement = cfg["unit"]
        self._attr_icon = cfg["icon"]

    @property
    def native_min_value(self) -> float:
        return float(self._min)

    @property
    def native_max_value(self) -> float:
        return float(self._max)

    @property
    def native_value(self) -> float:
        return float(self.coordinator.data.get(self._param_key, self._min))

    async def async_set_native_value(self, value: float) -> None:
        current = dict(self.coordinator.data)

        payload: dict[str, Any] = {
            "I_min_c": float(current.get("I_min_c", 1)),
            "I_max": float(current.get("I_max", 32)),
            "I_min_c1": float(current.get("I_min_c1", 1)),
            "I_max1": float(current.get("I_max1", 32)),
            "U_reseau": float(current.get("U_reseau", 240)),
            "P_charge_min": float(current.get("P_charge_min", 1300)),
            "P_charge_max": float(current.get("P_charge_max", -300)),
            "t_depassement": int(current.get("t_depassement", 15)),
            "t_delay_boucle": int(current.get("t_delay_boucle", 1000)),
            "ecran_type": int(current.get("ecran_type", 0)),
            "maxWhInput": int(current.get("maxWhInput", 0)),
            "DateHoraireDeFin": int(current.get("DateHoraireDeFin", 0)),
            "P_seuil_regul": float(current.get("P_seuil_regul", 0)),
            "fact_Icharge": float(current.get("fact_Icharge", 0)),
            "PAbonneReseau": float(current.get("PAbonneReseau", 9000)),
            "I_charge_manual1": float(current.get("I_charge_manual1", 12)),
        }

        if self._cast == "int":
            payload[self._param_key] = int(value)
        else:
            payload[self._param_key] = float(value)

        await self._api.save_params(payload)
        await self.coordinator.async_request_refresh()
