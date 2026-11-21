"""Config flow for the Iwona Pellets integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_FRAMING,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    CONF_START_COMMAND,
    CONF_SYNC_CLOCK,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_START_COMMAND,
    DEFAULT_SYNC_CLOCK,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    START_COMMANDS,
)
from .protocol import (
    FRAMING_RTU_OVER_TCP,
    FRAMINGS,
    ModbusClient,
    ModbusConnectionError,
    ModbusError,
    ModbusTimeout,
)
from .registers import BLOCK_STATES, to_address

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): NumberSelector(
            NumberSelectorConfig(min=1, max=247, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_FRAMING, default=FRAMING_RTU_OVER_TCP): SelectSelector(
            SelectSelectorConfig(
                options=list(FRAMINGS),
                translation_key="framing",
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


async def _async_test_connection(data: dict[str, Any]) -> None:
    """Read the state registers once; raises a ModbusError on failure."""
    client = ModbusClient(
        data[CONF_HOST], data[CONF_PORT], data[CONF_SLAVE], data[CONF_FRAMING], timeout=4
    )
    try:
        await client.read_holding(to_address(BLOCK_STATES[0]), BLOCK_STATES[1])
    finally:
        await client.close()


class IwonaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup of a stove."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            user_input = {
                **user_input,
                CONF_HOST: host,
                CONF_SLAVE: int(user_input[CONF_SLAVE]),  # the number box returns a float
                CONF_PORT: int(user_input[CONF_PORT]),
            }
            await self.async_set_unique_id(
                f"{host.lower()}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE]}"
            )
            self._abort_if_unique_id_configured()
            try:
                await _async_test_connection(user_input)
            except ModbusConnectionError:
                errors["base"] = "cannot_connect"
            except ModbusTimeout:
                errors["base"] = "no_response"
            except ModbusError:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error while testing the connection")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_HOST: host,
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_SLAVE: user_input[CONF_SLAVE],
                        CONF_FRAMING: user_input[CONF_FRAMING],
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> IwonaOptionsFlow:
        return IwonaOptionsFlow()


class IwonaOptionsFlow(OptionsFlow):
    """Polling interval and start command."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_START_COMMAND: int(user_input[CONF_START_COMMAND]),
                    CONF_SYNC_CLOCK: bool(user_input[CONF_SYNC_CLOCK]),
                }
            )
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=1,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_START_COMMAND,
                    default=str(options.get(CONF_START_COMMAND, DEFAULT_START_COMMAND)),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=list(START_COMMANDS),
                        translation_key="start_command",
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_SYNC_CLOCK,
                    default=options.get(CONF_SYNC_CLOCK, DEFAULT_SYNC_CLOCK),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
