from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_GPIO14_ACTION_NUMBER,
    CONF_GPIO5_ACTION_NUMBER,
    CONF_HCHP_INTENSITY_SOURCE,
    CONF_MANUAL_INTENSITY_SOURCE,
    DEFAULT_GPIO14_ACTION_NUMBER,
    DEFAULT_GPIO5_ACTION_NUMBER,
    INTENSITY_SOURCE_1,
    MODE_MANUEL,
)


def action_is_on(actions: dict[int, dict[str, Any]], num_action: int) -> bool:
    action = actions.get(int(num_action))
    if not action:
        return False
    try:
        if int(action.get("force", 0) or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    real_state = action.get("is_on")
    return bool(real_state) if real_state is not None else False


def _option_is_intensity1(entry: ConfigEntry, key: str) -> bool:
    return entry.options.get(key) == INTENSITY_SOURCE_1


async def async_sync_gpio14_for_intensity_source(
    coordinator,
    api,
    entry: ConfigEntry,
    *,
    target_mode: int | None = None,
    hchp_target_on: bool | None = None,
) -> None:
    """Force GPIO14 ON only when current logic requires Intensité 1.

    L'intensité secondaire ne s'applique qu'en mode Manuel : dans tous les
    autres modes (Auto, Semi-auto, Arrêt), on rebascule sur l'intensité
    principale, même si la plage HC/HP est active.
    """
    num_gpio14 = int(entry.data.get(CONF_GPIO14_ACTION_NUMBER, DEFAULT_GPIO14_ACTION_NUMBER) or 0)
    if num_gpio14 <= 0:
        return

    actions = (coordinator.data or {}).get("actions", {})

    raw_mode = target_mode if target_mode is not None else coordinator.data.get("mode")
    try:
        mode = int(raw_mode)
    except (TypeError, ValueError):
        mode = None
    is_manuel = mode == MODE_MANUEL

    manual_needs_gpio14 = is_manuel and _option_is_intensity1(
        entry, CONF_MANUAL_INTENSITY_SOURCE
    )

    num_gpio5 = int(entry.data.get(CONF_GPIO5_ACTION_NUMBER, DEFAULT_GPIO5_ACTION_NUMBER) or 0)
    hchp_on = hchp_target_on
    if hchp_on is None and num_gpio5 > 0:
        hchp_on = action_is_on(actions, num_gpio5)
    hchp_needs_gpio14 = (
        is_manuel
        and bool(hchp_on)
        and _option_is_intensity1(entry, CONF_HCHP_INTENSITY_SOURCE)
    )

    desired_on = manual_needs_gpio14 or hchp_needs_gpio14
    current_on = action_is_on(actions, num_gpio14)
    if current_on == desired_on:
        return

    await api.force_action(num_gpio14, 1440 if desired_on else 0)
