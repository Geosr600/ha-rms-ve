from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_GPIO14_ACTION_NUMBER,
    CONF_GPIO14_FORCE_VALUE,
    CONF_GPIO5_ACTION_NUMBER,
    CONF_HCHP_INTENSITY_SOURCE,
    CONF_MANUAL_INTENSITY_SOURCE,
    DEFAULT_GPIO14_ACTION_NUMBER,
    DEFAULT_GPIO14_FORCE_VALUE,
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
    """Force GPIO14 ON only when current logic requires Intensité 1."""
    num_gpio14 = int(entry.data.get(CONF_GPIO14_ACTION_NUMBER, DEFAULT_GPIO14_ACTION_NUMBER) or 0)
    if num_gpio14 <= 0:
        return

    actions = (coordinator.data or {}).get("actions", {})

    mode = target_mode if target_mode is not None else coordinator.data.get("mode")
    manual_needs_gpio14 = (
        mode == MODE_MANUEL
        and _option_is_intensity1(entry, CONF_MANUAL_INTENSITY_SOURCE)
    )

    num_gpio5 = int(entry.data.get(CONF_GPIO5_ACTION_NUMBER, DEFAULT_GPIO5_ACTION_NUMBER) or 0)
    hchp_on = hchp_target_on
    if hchp_on is None and num_gpio5 > 0:
        hchp_on = action_is_on(actions, num_gpio5)
    hchp_needs_gpio14 = bool(hchp_on) and _option_is_intensity1(
        entry, CONF_HCHP_INTENSITY_SOURCE
    )

    desired_on = manual_needs_gpio14 or hchp_needs_gpio14
    current_on = action_is_on(actions, num_gpio14)
    if current_on == desired_on:
        return

    force_value = int(entry.data.get(CONF_GPIO14_FORCE_VALUE, DEFAULT_GPIO14_FORCE_VALUE) or DEFAULT_GPIO14_FORCE_VALUE)
    await api.force_action(num_gpio14, force_value if desired_on else 0)
