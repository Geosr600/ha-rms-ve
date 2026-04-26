from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VERouterApi
from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_GPIO14_ACTION_NUMBER,
    CONF_GPIO5_ACTION_NUMBER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_GPIO14_ACTION_NUMBER,
    DEFAULT_GPIO5_ACTION_NUMBER,
    DOMAIN,
)


def _schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema({
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Borne de recharge")): str,
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
        vol.Required(CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
        vol.Required(CONF_GPIO14_ACTION_NUMBER, default=defaults.get(CONF_GPIO14_ACTION_NUMBER, DEFAULT_GPIO14_ACTION_NUMBER)): int,
        vol.Required(CONF_GPIO5_ACTION_NUMBER, default=defaults.get(CONF_GPIO5_ACTION_NUMBER, DEFAULT_GPIO5_ACTION_NUMBER)): int,
    })


class VERouterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])

            if scan_interval < 1 or scan_interval > 60:
                errors["base"] = "invalid_interval"
            else:
                session = async_get_clientsession(self.hass)
                api = VERouterApi(session, host)

                try:
                    data = await api.async_test_connection()
                    if "state" not in data:
                        errors["base"] = "invalid_response"
                    else:
                        await self.async_set_unique_id(host)
                        self._abort_if_unique_id_configured()

                        return self.async_create_entry(
                            title=user_input[CONF_NAME],
                            data={
                                CONF_NAME: user_input[CONF_NAME],
                                CONF_HOST: host,
                                CONF_SCAN_INTERVAL: scan_interval,
                                CONF_GPIO14_ACTION_NUMBER: int(user_input[CONF_GPIO14_ACTION_NUMBER]),
                                CONF_GPIO5_ACTION_NUMBER: int(user_input[CONF_GPIO5_ACTION_NUMBER]),
                            },
                        )
                except Exception:
                    errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", data_schema=_schema(), errors=errors)

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])

            if scan_interval < 1 or scan_interval > 60:
                errors["base"] = "invalid_interval"
            else:
                session = async_get_clientsession(self.hass)
                api = VERouterApi(session, host)

                try:
                    data = await api.async_test_connection()
                    if "state" not in data:
                        errors["base"] = "invalid_response"
                    else:
                        self.hass.config_entries.async_update_entry(
                            entry,
                            title=user_input[CONF_NAME],
                            data={
                                CONF_NAME: user_input[CONF_NAME],
                                CONF_HOST: host,
                                CONF_SCAN_INTERVAL: scan_interval,
                                CONF_GPIO14_ACTION_NUMBER: int(user_input[CONF_GPIO14_ACTION_NUMBER]),
                                CONF_GPIO5_ACTION_NUMBER: int(user_input[CONF_GPIO5_ACTION_NUMBER]),
                            },
                        )
                        await self.hass.config_entries.async_reload(entry.entry_id)
                        return self.async_abort(reason="reconfigured")
                except Exception:
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(dict(entry.data)),
            errors=errors,
        )
