from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VERouterApi
from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class VERouterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            scan = int(user_input[CONF_SCAN_INTERVAL])

            if scan < 1 or scan > 60:
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
                                CONF_SCAN_INTERVAL: scan,
                            },
                        )

                except Exception as e:
                    _LOGGER.error("Connection error: %s", e)
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Borne VE"): str,
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        errors = {}

        if user_input is not None:
            scan = int(user_input[CONF_SCAN_INTERVAL])

            if scan < 1 or scan > 60:
                errors["base"] = "invalid_interval"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_SCAN_INTERVAL: scan,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=entry.data.get(CONF_NAME)): str,
                    vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST)): str,
                    vol.Required(CONF_SCAN_INTERVAL, default=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
                }
            ),
            errors=errors,
        )
