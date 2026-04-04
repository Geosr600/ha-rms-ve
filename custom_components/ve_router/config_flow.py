from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig

from .api import VERouterApi
from .const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_SCAN_INTERVAL, MIN_SCAN_INTERVAL


class VERouterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            api = VERouterApi(session, host)

            try:
                data = await api.async_test_connection()
                if "state" not in data:
                    errors["base"] = "invalid_response"
                else:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={CONF_NAME: user_input[CONF_NAME], CONF_HOST: host},
                        options={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])},
                    )
            except Exception:
                errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required(CONF_NAME, default="Borne de recharge"): str,
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
                NumberSelectorConfig(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, step=1, mode="box")
            ),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return VERouterOptionsFlow(config_entry)


class VERouterOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])})

        current_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=current_interval): NumberSelector(
                NumberSelectorConfig(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, step=1, mode="box")
            ),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
