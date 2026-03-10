"""Config flow for NAAF/YR Pollen Forecast integration."""
from typing import Any

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN


class PollenvarselConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NAAF/YR Pollen Forecast."""

    VERSION = 1

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import of configuration from configuration.yaml."""
        return self.async_create_entry(
            title="NAAF/YR Pollen Forecast",
            data=import_data,
        )
