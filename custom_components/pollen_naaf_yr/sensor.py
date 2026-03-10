"""NAAF Pollen Forecast Sensors."""
import logging
from typing import Any, Final

import aiohttp
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from datetime import datetime, timedelta

_LOGGER: logging.Logger = logging.getLogger(__name__)

DOMAIN: Final = "pollenvarsel_naaf_yr"
CONF_LOCATIONS: Final = "locations"
CONF_LOCATION_ID: Final = "location_id"
CONF_LOCATION_NAME: Final = "location_name"
CONF_POLLEN_TYPES: Final = "pollen_types"
CONF_UPDATE_FREQUENCY: Final = "update_frequency"
CONF_LANGUAGE: Final = "language"
DEFAULT_UPDATE_FREQUENCY: Final = 3
DEFAULT_LANGUAGE: Final = "nb"

TRANSLATIONS: Final = {
    "nb": {"today": "I dag", "tomorrow": "I morgen", "pollen": "Pollen"},
    "nn": {"today": "I dag", "tomorrow": "I morgon", "pollen": "Pollen"},
    "sme": {"today": "Odne", "tomorrow": "Ihttin", "pollen": "Pollen"},
    "en": {"today": "Today", "tomorrow": "Tomorrow", "pollen": "Pollen"},
}

BASE_URL: Final = "https://www.yr.no/api/v0/locations"


class PollenDataCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching pollen data."""

    def __init__(
        self,
        hass: HomeAssistant,
        location_id: str,
        language: str = DEFAULT_LANGUAGE,
        update_frequency: int = DEFAULT_UPDATE_FREQUENCY,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"NAAF Pollen {location_id}",
            update_interval=timedelta(hours=update_frequency),
        )
        self.location_id = location_id
        self.language = language
        self.region_name: str = location_id
        self.last_updated_at: str | None = None
        self.data = {"today": {}, "tomorrow": {}}

    async def _async_update_data(self) -> dict:
        """Fetch pollen data from NAAF API."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{BASE_URL}/{self.location_id}/pollen?language={self.language}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"API returned {resp.status}")
                    data = await resp.json()

            embedded = data.get("_embedded", {})
            self.region_name = embedded.get("regionName", self.location_id)
            self.last_updated_at = datetime.now().isoformat()

            # Parse the response
            forecast = embedded.get("pollenForecast", [])
            parsed_data = {"today": {}, "tomorrow": {}}

            for day_idx, day_forecast in enumerate(forecast[:2]):
                day_key = "today" if day_idx == 0 else "tomorrow"
                distributions = day_forecast.get("distributions", {})
                date = day_forecast.get("date")

                # Flatten the distribution structure
                for level, level_data in distributions.items():
                    if "pollenTypes" in level_data:
                        distribution_name = level_data.get("distributionName")
                        for pollen in level_data["pollenTypes"]:
                            pollen_id = pollen.get("id")
                            pollen_name = pollen.get("name")
                            if pollen_id:
                                parsed_data[day_key][pollen_id] = {
                                    "level": level,
                                    "level_name": distribution_name,
                                    "pollen_name": pollen_name,
                                    "date": date,
                                }

            return parsed_data

        except UpdateFailed as err:
            raise err
        except Exception as err:
            raise UpdateFailed(f"Error fetching pollen data: {err}") from err


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up pollen sensors from config entry."""
    config_data = entry.data
    
    locations = config_data.get(CONF_LOCATIONS, [])
    pollen_types = config_data.get(CONF_POLLEN_TYPES, [])
    update_frequency = config_data.get(CONF_UPDATE_FREQUENCY, DEFAULT_UPDATE_FREQUENCY)
    language = config_data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

    entities = []

    for location in locations:
        location_id = location.get(CONF_LOCATION_ID)
        custom_location_name = location.get(CONF_LOCATION_NAME)

        # Create coordinator for this location
        coordinator = PollenDataCoordinator(hass, location_id, language, update_frequency)
        await coordinator.async_config_entry_first_refresh()

        # Display name is custom name or region name from API
        display_name = custom_location_name or coordinator.region_name

        # Create device info for this location
        device_info = DeviceInfo(
            identifiers={(DOMAIN, location_id)},
            name=display_name,
            manufacturer="YR/NAAF",
        )

        # Create sensors for each pollen type and forecast day
        for pollen_type in pollen_types:
            for day in ["today", "tomorrow"]:
                sensor = PollenSensor(
                    coordinator,
                    location_id,
                    custom_location_name,
                    pollen_type,
                    day,
                    entry.entry_id,
                    device_info,
                )
                entities.append(sensor)

    async_add_entities(entities)


class PollenSensor(CoordinatorEntity, SensorEntity):
    """Sensor for pollen level."""

    _attr_attribution = "Data from NAAF (Norwegian Asthma and Allergy Association)"

    def __init__(
        self,
        coordinator: PollenDataCoordinator,
        location_id: str,
        custom_location_name: str | None,
        pollen_type: str,
        day: str,
        entry_id: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.pollen_type = pollen_type
        self.day = day
        self.location_id = location_id
        self.custom_location_name = custom_location_name
        self.entry_id = entry_id
        self._display_name = custom_location_name or coordinator.region_name

        self._attr_unique_id = (
            f"{DOMAIN}_{location_id}_{pollen_type.lower()}_{day}"
        )
        self._attr_device_info = device_info
        self._attr_icon = self._get_icon()

    @property
    def name(self) -> str:
        """Return localized sensor name."""
        language = self.coordinator.language
        translations = TRANSLATIONS.get(language, TRANSLATIONS["en"])
        day_text = translations[self.day]

        # Use localized pollen name from API data if available
        today_data = self.coordinator.data.get("today", {})
        pollen_data = today_data.get(self.pollen_type, {})
        pollen_name = pollen_data.get("pollen_name", self.pollen_type)

        return f"{translations['pollen']} {pollen_name} {self._display_name} {day_text}"

    def _get_icon(self) -> str:
        """Get icon based on pollen type."""
        icons = {
            "hazel": "mdi:tree",
            "alder": "mdi:tree",
            "willow": "mdi:tree",
            "birch": "mdi:tree",
            "grass": "mdi:grass",
            "mugwort": "mdi:flower",
        }
        return icons.get(self.pollen_type.lower(), "mdi:flower-pollen")

    @property
    def state(self) -> str | None:
        """Return pollen level."""
        if not self.coordinator.data:
            return None

        day_data = self.coordinator.data.get(self.day, {})
        pollen_data = day_data.get(self.pollen_type, {})
        return pollen_data.get("level", "none")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        day_data = self.coordinator.data.get(self.day, {})
        pollen_data = day_data.get(self.pollen_type, {})

        attrs: dict[str, Any] = {
            "date": pollen_data.get("date"),
            "pollen_name": pollen_data.get("pollen_name"),
            "region_name": self.coordinator.region_name,
            "last_updated": self.coordinator.last_updated_at,
        }
        if pollen_data.get("level_name"):
            attrs["level_name"] = pollen_data.get("level_name")
        if self.custom_location_name:
            attrs["location_name"] = self.custom_location_name
        return attrs
