from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL, MODE_LABELS


def _state_letter(value):
    if value in ("A", "B", "C", "F"):
        return value
    return "Inconnu"


def _state_text(value):
    mapping = {
        "A": "Pas de véhicule",
        "B": "Véhicule connecté",
        "C": "Charge en cours",
        "F": "Défaut",
    }
    return mapping.get(value, "Inconnu")


def _format_mode(value):
    return MODE_LABELS.get(value, "Inconnu")


def _format_charge_time(ms):
    total_s = int((ms or 0) / 1000)
    h = total_s // 3600
    m = (total_s % 3600) // 60
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _num(data, key, default=None):
    value = data.get(key, default)
    if value is None:
        return default
    try:
        if isinstance(value, str) and value.strip() == "":
            return default
        if "." in str(value):
            return float(value)
        return int(value)
    except Exception:
        try:
            return float(value)
        except Exception:
            return default


def _energy_wh(data):
    value = _num(data, "EnergieCharge_Wh", None)
    if value is None:
        value = _num(data, "EnergieChargee_Wh", None)
    return value


def _power_kw(data):
    u = _num(data, "U_reseau", 0) or 0
    i = _num(data, "I_charge", 0) or 0
    return round((float(u) * float(i)) / 1000, 3)


SENSORS = [
    ("mode", "Mode de fonctionnement", lambda d: _format_mode(d.get("mode")), None, "mdi:cog", True, False),
    ("state_text", "État de la liaison", lambda d: _state_text(d.get("state")), None, "mdi:ev-plug-type2", True, False),
    ("state_code", "État de la liaison code", lambda d: _state_letter(d.get("state")), None, "mdi:alphabetical", True, False),
    ("I_charge", "Courant de charge VE", lambda d: _num(d, "I_charge", None), "A", "mdi:current-ac", True, False),
    ("Puissance_charge_kW", "Puissance de charge", lambda d: _power_kw(d), "kW", "mdi:flash", True, False),
    ("EnergieCharge_Wh", "Recharge cumulée VE", lambda d: _energy_wh(d), "Wh", "mdi:battery-charging", True, False),
    ("TempsCharge_ms", "Temps de charge VE", lambda d: _format_charge_time(_num(d, "TempsCharge_ms", 0)), None, "mdi:timer-outline", True, False),
    ("U_reseau", "U_reseau", lambda d: _num(d, "U_reseau", None), "V", "mdi:sine-wave", True, False),
    ("cp_pwm_charging", "PWM borne VE", lambda d: _num(d, "cp_pwm_charging", None), "%", "mdi:sine-wave", True, True),
    ("nb_depassement_hard", "nb_depassement_hard", lambda d: _num(d, "nb_depassement_hard", None), None, "mdi:alert", True, True),
    ("nb_depassement_soft", "nb_depassement_soft", lambda d: _num(d, "nb_depassement_soft", None), None, "mdi:alert-outline", True, True),
    ("I_max", "I_max", lambda d: _num(d, "I_max", None), "A", "mdi:arrow-collapse-up", True, True),
    ("I_min_c", "I_min_c", lambda d: _num(d, "I_min_c", None), "A", "mdi:arrow-collapse-down", True, True),
    ("Version", "Version", lambda d: d.get("Version"), None, "mdi:information-outline", True, True),
    ("DateVersion", "DateVersion", lambda d: d.get("DateVersion"), None, "mdi:calendar", True, True),
    ("CarteVersion", "CarteVersion", lambda d: d.get("CarteVersion"), None, "mdi:chip", True, True),
    ("PuissanceS_M", "Puissance S VE", lambda d: _num(d, "PuissanceS_M", None), "W", "mdi:flash-outline", False, True),
    ("maxWhInput", "maxWhInput", lambda d: _num(d, "maxWhInput", None), "Wh", "mdi:battery-plus-outline", False, True),
    ("DateHoraireDefin", "DateHoraireDefin", lambda d: _num(d, "DateHoraireDefin", None), None, "mdi:calendar-clock", False, True),
    ("P_seuil_regul", "P_seuil_regul", lambda d: _num(d, "P_seuil_regul", None), None, "mdi:tune", False, True),
    ("fact_Icharge", "fact_Icharge", lambda d: _num(d, "fact_Icharge", None), None, "mdi:math-compass", False, True),
    ("PuissanceI_M", "Production-Consommation VE", lambda d: _num(d, "PuissanceI_M", None), "W", "mdi:home-lightning-bolt-outline", False, True),
]


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [
        VERouterSensor(coordinator, entry, key, name, value_fn, unit, icon, enabled, diagnostic)
        for key, name, value_fn, unit, icon, enabled, diagnostic in SENSORS
    ]
    async_add_entities(entities)


class VERouterSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, value_fn, unit, icon, enabled, diagnostic) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._value_fn = value_fn
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_entity_registry_enabled_default = enabled
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        try:
            return self._value_fn(self.coordinator.data)
        except Exception:
            return None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
