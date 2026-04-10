from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL


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
}


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities: list[NumberEntity] = [
        VERouterManualCurrentNumber(coordinator, api, entry),
        VERouterEnergyWhNumber(coordinator, api, entry),
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
        await self._api.set_current(int(value))
        await self.coordinator.async_request_refresh()


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
        }

        if self._cast == "int":
            payload[self._param_key] = int(value)
        else:
            payload[self._param_key] = float(value)

        await self._api.save_params(payload)
        await self.coordinator.async_request_refresh()
