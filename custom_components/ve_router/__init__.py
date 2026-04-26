from __future__ import annotations

from pathlib import Path
import logging
import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VERouterApi
from .const import (
    ATTR_CURRENT,
    ATTR_ENTRY_ID,
    ATTR_MODE,
    CONF_HOST,
    CONF_ON_PLUG_ACTION,
    CONF_ON_UNPLUG_ACTION,
    CONF_SOC_LIMIT_ENABLED,
    CONF_TARGET_SOC,
    CONF_VEHICLE_SOC_ENTITY,
    CONF_SCAN_INTERVAL,
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

PLATFORMS = ["sensor", "binary_sensor", "number", "datetime", "select", "switch", "text"]
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
    """Best-effort registration of the bundled Lovelace card resource."""
    resource_url = "/ve_router/frontend/rms-ve-card.js?v=0.7.7"

    try:
        # Home Assistant stores Lovelace resources in hass.data["lovelace"]["resources"].
        # Older/variant builds may expose an object with a .resources attribute. Support both.
        lovelace = hass.data.get("lovelace")
        resources = None
        if isinstance(lovelace, dict):
            resources = lovelace.get("resources")
        elif lovelace is not None:
            resources = getattr(lovelace, "resources", None)

        if resources is None:
            _LOGGER.debug("Lovelace resources API indisponible; carte RMS VE non auto-enregistrée")
            return

        items_result = resources.async_items() if hasattr(resources, "async_items") else []
        if hasattr(items_result, "__await__"):
            items_result = await items_result
        items = list(items_result or [])
        for item in items:
            url = str(item.get("url", ""))
            if url.startswith("/ve_router/frontend/rms-ve-card.js"):
                if url == resource_url:
                    return

                item_id = item.get("id")
                if item_id and hasattr(resources, "async_update_item"):
                    await resources.async_update_item(
                        item_id, {"res_type": "module", "url": resource_url}
                    )
                    _LOGGER.info(
                        "Ressource Lovelace RMS VE mise à jour: %s -> %s",
                        url,
                        resource_url,
                    )
                    return

                if item_id and hasattr(resources, "async_delete_item"):
                    await resources.async_delete_item(item_id)
                    break

        await resources.async_create_item({"res_type": "module", "url": resource_url})
        _LOGGER.info("Carte Lovelace RMS VE enregistrée automatiquement: %s", resource_url)
    except Exception as err:
        _LOGGER.debug("Impossible d'enregistrer automatiquement la carte RMS VE: %s", err)


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
