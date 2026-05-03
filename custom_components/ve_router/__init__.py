from __future__ import annotations

from pathlib import Path
from datetime import timedelta
from uuid import uuid4
import logging
import voluptuous as vol

from homeassistant.util import dt as dt_util

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import VERouterApi
from .const import (
    ATTR_CURRENT,
    ATTR_ENTRY_ID,
    ATTR_MODE,
    CONF_HOST,
    CONF_GPIO5_ACTION_NUMBER,
    CONF_HC_ENABLED,
    CONF_HC_START_TIME,
    CONF_HC_END_TIME,
    CONF_ON_PLUG_ACTION,
    CONF_ON_UNPLUG_ACTION,
    CONF_SOC_LIMIT_ENABLED,
    CONF_TARGET_SOC,
    CONF_VEHICLE_SOC_ENTITY,
    CONF_SCAN_INTERVAL,
    DEFAULT_GPIO5_ACTION_NUMBER,
    DEFAULT_HC_START_TIME,
    DEFAULT_HC_END_TIME,
    DEFAULT_ON_PLUG_ACTION,
    DEFAULT_ON_UNPLUG_ACTION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MODE_AUTO,
    MODE_LABELS,
    MODE_MANUEL,
    MODE_SEMI_AUTO,
    PLUG_ACTION_TO_MODE,
    SERVICE_SET_CURRENT,
    SERVICE_SET_MODE,
)
from .coordinator import VERouterCoordinator
from .gpio_logic import async_sync_gpio14_for_intensity_source

PLATFORMS = ["sensor", "binary_sensor", "number", "datetime", "select", "switch", "text", "time"]
_LOGGER = logging.getLogger(__name__)


def _normalize_mode(value: str | int) -> int:
    if isinstance(value, int):
        if value in MODE_LABELS:
            return value
        raise vol.Invalid(f"Mode invalide: {value}")

    text = str(value).strip()
    if text.isdigit():
        number = int(text)
        if number in MODE_LABELS:
            return number
        raise vol.Invalid(f"Mode invalide: {value}")

    for mode, label in MODE_LABELS.items():
        if text.casefold() == label.casefold():
            return mode

    raise vol.Invalid(f"Mode invalide: {value}")


def _entry_id_from_call(hass: HomeAssistant, call: ServiceCall) -> str:
    entry_id = call.data.get(ATTR_ENTRY_ID)
    if entry_id:
        if entry_id in hass.data.get(DOMAIN, {}):
            return entry_id
        raise vol.Invalid(f"entry_id inconnu: {entry_id}")

    device_id = call.data.get(ATTR_DEVICE_ID)
    if device_id:
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device:
            for identifier_domain, identifier in device.identifiers:
                if identifier_domain == DOMAIN and identifier in hass.data.get(DOMAIN, {}):
                    return identifier
        raise vol.Invalid("Aucun équipement RMS VE correspondant à ce device_id")

    entries = list(hass.data.get(DOMAIN, {}).keys())
    if len(entries) == 1:
        return entries[0]

    raise vol.Invalid("Précise entry_id ou target.device_id")


async def async_setup(hass: HomeAssistant, config) -> bool:
    frontend_path = Path(__file__).parent / "frontend"
    if hass.http is not None:
        await hass.http.async_register_static_paths(
            [StaticPathConfig("/ve_router/frontend", str(frontend_path), False)]
        )

    @callback
    def _register_resource(_event) -> None:
        hass.async_create_task(_async_register_card_resource(hass))

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_resource)
    return True


def _parse_hhmm(value: str, default: str) -> int:
    """Return minutes since midnight for an HH:MM value."""
    text = str(value or default)[:5]
    try:
        hour, minute = text.split(":")
        return int(hour) * 60 + int(minute)
    except (TypeError, ValueError):
        hour, minute = default[:5].split(":")
        return int(hour) * 60 + int(minute)


def _hc_window_state(now_minutes: int, start_minutes: int, end_minutes: int, today) -> tuple[bool, str]:
    """Return whether now is inside the HC window and a stable window key.

    Supports same-day windows (13:00 -> 16:00) and overnight windows
    (22:00 -> 06:00). If start == end, the window is treated as disabled.
    """
    if start_minutes == end_minutes:
        return False, ""

    if start_minutes < end_minutes:
        return start_minutes <= now_minutes < end_minutes, today.isoformat()

    # Overnight window. Between midnight and end time belongs to yesterday's window.
    if now_minutes >= start_minutes:
        return True, today.isoformat()
    if now_minutes < end_minutes:
        previous_day = today - timedelta(days=1)
        return True, previous_day.isoformat()
    return False, today.isoformat()


async def _force_hc_off_if_needed(
    entry_state: dict,
    coordinator: VERouterCoordinator,
    api: VERouterApi,
    entry: ConfigEntry,
    num_action: int,
) -> None:
    actions = (coordinator.data or {}).get("actions", {})
    action = actions.get(num_action)
    force_is_on = False
    if action is not None:
        try:
            force_is_on = int(action.get("force", 0) or 0) > 0
        except (TypeError, ValueError):
            force_is_on = False

    if entry_state.get("hc_window_active") or force_is_on:
        await api.force_action(num_action, 0)
        await async_sync_gpio14_for_intensity_source(
            coordinator,
            api,
            entry,
            hchp_target_on=False,
        )
        entry_state["hc_window_active"] = False
        await coordinator.async_request_refresh()


async def _apply_hc_schedule(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: VERouterCoordinator,
    api: VERouterApi,
) -> None:
    """Activate GPIO5 during the configured HC window."""
    if not bool(entry.options.get(CONF_HC_ENABLED, False)):
        return

    start_time = str(entry.options.get(CONF_HC_START_TIME, DEFAULT_HC_START_TIME) or DEFAULT_HC_START_TIME)
    end_time = str(entry.options.get(CONF_HC_END_TIME, DEFAULT_HC_END_TIME) or DEFAULT_HC_END_TIME)
    now = dt_util.now()
    now_minutes = now.hour * 60 + now.minute
    start_minutes = _parse_hhmm(start_time, DEFAULT_HC_START_TIME)
    end_minutes = _parse_hhmm(end_time, DEFAULT_HC_END_TIME)
    in_window, window_key = _hc_window_state(now_minutes, start_minutes, end_minutes, now.date())

    entry_state = hass.data[DOMAIN][entry.entry_id]
    num_action = int(entry.data.get(CONF_GPIO5_ACTION_NUMBER, DEFAULT_GPIO5_ACTION_NUMBER) or 0)
    if num_action <= 0:
        if in_window and entry_state.get("last_hc_trigger_key") != window_key:
            _LOGGER.warning("HC activé mais NumAction GPIO5 invalide pour %s", entry.title)
            entry_state["last_hc_trigger_key"] = window_key
        return

    if not in_window:
        await _force_hc_off_if_needed(entry_state, coordinator, api, entry, num_action)
        return

    if entry_state.get("last_hc_trigger_key") == window_key:
        entry_state["hc_window_active"] = True
        return

    _LOGGER.info(
        "Fenêtre HC active sur %s (%s -> %s): activation GPIO5 action %s",
        entry.title,
        start_time[:5],
        end_time[:5],
        num_action,
    )
    await api.force_action(num_action, 1440)
    await async_sync_gpio14_for_intensity_source(
        coordinator,
        api,
        entry,
        hchp_target_on=True,
    )
    entry_state["last_hc_trigger_key"] = window_key
    entry_state["hc_window_active"] = True
    await coordinator.async_request_refresh()


async def _apply_vehicle_actions(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: VERouterCoordinator,
    api: VERouterApi,
) -> None:
    state = str(coordinator.data.get("state", "")).strip().upper()
    connected = state in {"B", "C"}

    previous_connected = hass.data[DOMAIN][entry.entry_id].get("vehicle_connected")
    hass.data[DOMAIN][entry.entry_id]["vehicle_connected"] = connected

    if previous_connected is None or previous_connected == connected:
        return

    action_key = None
    event_label = None

    if (not previous_connected) and connected:
        action_key = entry.options.get(CONF_ON_PLUG_ACTION, DEFAULT_ON_PLUG_ACTION)
        event_label = "branchement"
    elif previous_connected and (not connected):
        action_key = entry.options.get(CONF_ON_UNPLUG_ACTION, DEFAULT_ON_UNPLUG_ACTION)
        event_label = "débranchement"

    mode = PLUG_ACTION_TO_MODE.get(action_key)
    if mode is None:
        return

    current_mode = coordinator.data.get("mode")
    if current_mode == mode:
        return

    _LOGGER.info(
        "Véhicule détecté sur %s: action de %s '%s' -> mode %s",
        entry.title,
        event_label,
        action_key,
        MODE_LABELS[mode],
    )
    await api.set_mode(mode)
    await async_sync_gpio14_for_intensity_source(
        coordinator,
        api,
        entry,
        target_mode=mode,
    )
    await coordinator.async_request_refresh()


async def _apply_target_soc_limit(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: VERouterCoordinator,
    api: VERouterApi,
) -> None:
    """Switch back to Auto when the external vehicle SOC reaches the target."""
    if not bool(entry.options.get(CONF_SOC_LIMIT_ENABLED, False)):
        return

    current_mode = int(coordinator.data.get("mode", MODE_AUTO) or MODE_AUTO)
    if current_mode not in {MODE_MANUEL, MODE_SEMI_AUTO}:
        return

    entity_id = str(entry.options.get(CONF_VEHICLE_SOC_ENTITY, "") or "").strip()
    if not entity_id:
        return

    state = hass.states.get(entity_id)
    if state is None:
        _LOGGER.debug("Entité SOC véhicule introuvable: %s", entity_id)
        return

    try:
        current_soc = float(str(state.state).replace(",", "."))
    except (TypeError, ValueError):
        _LOGGER.debug("SOC véhicule non numérique pour %s: %s", entity_id, state.state)
        return

    try:
        target_soc = float(entry.options.get(CONF_TARGET_SOC, 80))
    except (TypeError, ValueError):
        target_soc = 80.0

    if current_soc < target_soc:
        return

    _LOGGER.info(
        "SOC véhicule atteint %.1f%% / %.1f%% sur %s: passage en Auto",
        current_soc,
        target_soc,
        entry.title,
    )
    await api.set_mode(MODE_AUTO)
    await async_sync_gpio14_for_intensity_source(
        coordinator,
        api,
        entry,
        target_mode=MODE_AUTO,
    )
    await coordinator.async_request_refresh()


async def _async_register_card_resource(hass: HomeAssistant) -> None:
    """Safely add/update only the RMS VE Lovelace card resource.

    Important: Home Assistant stores Lovelace resources with the key
    `type` in storage, while some runtime APIs use `res_type`.
    To avoid a blank Type column in the UI, this function always writes
    both keys when possible and never replaces unrelated resources.
    """
    resource_url = "/ve_router/frontend/rms-ve-card.js?v=0.9.1"
    resource_base = "/ve_router/frontend/rms-ve-card.js"

    # Preferred path: use the Lovelace resource storage collection already loaded by HA.
    # Do not return early: we still patch storage afterwards to repair old entries
    # created without a visible `type`.
    try:
        lovelace_data = hass.data.get("lovelace")
        resource_collection = None
        if isinstance(lovelace_data, dict):
            resource_collection = lovelace_data.get("resources")

        if resource_collection is not None and hasattr(resource_collection, "async_items"):
            items = list(resource_collection.async_items())
            rms_items = [
                item
                for item in items
                if resource_base in str(item.get("url", ""))
                or "rms-ve-card.js" in str(item.get("url", ""))
            ]

            payload = {"res_type": "module", "type": "module", "url": resource_url}

            if not rms_items:
                await resource_collection.async_create_item(payload)
                _LOGGER.info("Ressource Lovelace RMS VE ajoutée: %s", resource_url)
            else:
                first = rms_items[0]
                first_id = first.get("id")
                current_type = first.get("type") or first.get("res_type")
                if first_id and (first.get("url") != resource_url or current_type != "module"):
                    await resource_collection.async_update_item(first_id, payload)
                    _LOGGER.info("Ressource Lovelace RMS VE mise à jour: %s", resource_url)

                # Remove only duplicate RMS VE resources, never unrelated resources.
                if hasattr(resource_collection, "async_delete_item"):
                    for duplicate in rms_items[1:]:
                        duplicate_id = duplicate.get("id")
                        if duplicate_id:
                            await resource_collection.async_delete_item(duplicate_id)
    except Exception as err:
        _LOGGER.debug("Ajout ressource RMS VE via collection Lovelace impossible: %s", err)

    # Storage patch. Preserves every unrelated resource and repairs old RMS entries
    # where the Type column was blank.
    try:
        store: Store[dict] = Store(hass, 1, "lovelace_resources", minor_version=1)
        data = await store.async_load()
        if not isinstance(data, dict):
            data = {"items": []}

        items = data.get("items")
        if not isinstance(items, list):
            items = []

        kept_items = []
        rms_item = None
        changed = False

        for item in items:
            if not isinstance(item, dict):
                kept_items.append(item)
                continue

            url = str(item.get("url", ""))
            if "rms-ve-card.js" not in url:
                kept_items.append(item)
                continue

            if rms_item is None:
                rms_item = dict(item)
                if rms_item.get("url") != resource_url:
                    rms_item["url"] = resource_url
                    changed = True
                if rms_item.get("type") != "module":
                    rms_item["type"] = "module"
                    changed = True
                if rms_item.get("res_type") != "module":
                    rms_item["res_type"] = "module"
                    changed = True
                if not rms_item.get("id"):
                    rms_item["id"] = uuid4().hex
                    changed = True
            else:
                changed = True

        if rms_item is None:
            rms_item = {
                "id": uuid4().hex,
                "type": "module",
                "res_type": "module",
                "url": resource_url,
            }
            changed = True

        new_items = kept_items + [rms_item]
        if new_items != items:
            changed = True

        if changed:
            data["items"] = new_items
            await store.async_save(data)
            _LOGGER.info("Ressource Lovelace RMS VE enregistrée automatiquement: %s", resource_url)
    except Exception as err:
        _LOGGER.warning("Impossible d'enregistrer automatiquement la carte RMS VE: %s", err)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = VERouterApi(session, entry.data[CONF_HOST])
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = VERouterCoordinator(hass, api, scan_interval, config_entry=entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    initial_state = str(coordinator.data.get("state", "")).strip().upper()
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "vehicle_connected": initial_state in {"B", "C"},
        "last_hc_trigger_key": None,
        "hc_window_active": False,
    }
    # Try again here: async_setup can run before Lovelace resources are initialized.
    hass.async_create_task(_async_register_card_resource(hass))


    @callback
    def _handle_coordinator_update() -> None:
        hass.async_create_task(_apply_vehicle_actions(hass, entry, coordinator, api))
        hass.async_create_task(
            async_sync_gpio14_for_intensity_source(coordinator, api, entry)
        )
        hass.async_create_task(_apply_target_soc_limit(hass, entry, coordinator, api))
        hass.async_create_task(_apply_hc_schedule(hass, entry, coordinator, api))

    remove_listener = coordinator.async_add_listener(_handle_coordinator_update)
    hass.data[DOMAIN][entry.entry_id]["remove_listener"] = remove_listener

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    if not hass.services.has_service(DOMAIN, SERVICE_SET_MODE):

        async def handle_set_mode(call: ServiceCall) -> None:
            target_entry_id = _entry_id_from_call(hass, call)
            data = hass.data[DOMAIN][target_entry_id]
            mode = _normalize_mode(call.data[ATTR_MODE])
            await data["api"].set_mode(mode)
            await async_sync_gpio14_for_intensity_source(
                data["coordinator"],
                data["api"],
                hass.config_entries.async_get_entry(target_entry_id),
                target_mode=mode,
            )
            await data["coordinator"].async_request_refresh()

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_MODE,
            handle_set_mode,
            schema=vol.Schema(
                {
                    vol.Optional(ATTR_ENTRY_ID): cv.string,
                    vol.Optional(ATTR_DEVICE_ID): cv.string,
                    vol.Required(ATTR_MODE): vol.Any(cv.string, vol.Coerce(int)),
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_CURRENT):

        async def handle_set_current(call: ServiceCall) -> None:
            target_entry_id = _entry_id_from_call(hass, call)
            data = hass.data[DOMAIN][target_entry_id]
            current = float(call.data[ATTR_CURRENT])
            if current < 1:
                raise vol.Invalid("Le courant doit être supérieur ou égal à 1 A")
            await data["api"].set_current(current)
            await data["coordinator"].async_request_refresh()

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CURRENT,
            handle_set_current,
            schema=vol.Schema(
                {
                    vol.Optional(ATTR_ENTRY_ID): cv.string,
                    vol.Optional(ATTR_DEVICE_ID): cv.string,
                    vol.Required(ATTR_CURRENT): vol.Coerce(float),
                }
            ),
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if unload_ok and entry_data:
        remove_listener = entry_data.get("remove_listener")
        if remove_listener:
            remove_listener()

        hass.data[DOMAIN].pop(entry.entry_id, None)

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_MODE)
            hass.services.async_remove(DOMAIN, SERVICE_SET_CURRENT)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
