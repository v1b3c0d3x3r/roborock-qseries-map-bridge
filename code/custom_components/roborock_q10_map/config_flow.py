from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import CONF_POLL_INTERVAL, CONF_ROBOTS, DEFAULT_NAME, DEFAULT_POLL_INTERVAL, DEFAULT_ROBOTS, DOMAIN


class RoborockQ10MapConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            robots = [value.strip() for value in user_input[CONF_ROBOTS].split(",") if value.strip()]
            if not robots:
                errors[CONF_ROBOTS] = "no_robots"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={
                        CONF_ROBOTS: robots,
                        CONF_POLL_INTERVAL: max(1, int(user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ROBOTS, default=DEFAULT_ROBOTS): str,
                    vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
                }
            ),
            errors=errors,
        )
