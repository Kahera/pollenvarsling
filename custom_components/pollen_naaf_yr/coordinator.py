"""Data coordinator for NAAF Pollen Forecast integration."""
import logging
from datetime import datetime, timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import BASE_URL, DEFAULT_LANGUAGE, DEFAULT_UPDATE_FREQUENCY

_LOGGER: logging.Logger = logging.getLogger(__name__)


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
        self.pollen_names: dict[str, str] = {}
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
                                if pollen_name:
                                    self.pollen_names[pollen_id] = pollen_name

            return parsed_data

        except UpdateFailed as err:
            raise err
        except Exception as err:
            raise UpdateFailed(f"Error fetching pollen data: {err}") from err
