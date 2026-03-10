# Pollenvarsel Integration

A custom Home Assistant integration for displaying Norwegian pollen forecasts from NAAF (Norwegian Asthma and Allergy Association) for multiple locations.

## Installation

### Via HACS (Recommended)
1. Go to HACS > Integrations
2. Click the menu (⋮) and select "Custom repositories"
3. Add `https://github.com/kahera/pollenvarsling` as a Custom Repository
4. Select the category "Integration"
5. Search for "Pollenvarsel" and install

### Manual
Copy the `custom_components/pollen_naaf_yr` folder to your `custom_components` directory in Home Assistant.

## Configuration

Add this to your `configuration.yaml`:

```yaml
pollenvarsel_naaf_yr:
  pollen_types:
    - Hassel
    - Or
    - Salix
    - Bjørk
    - Gress
    - Burot
  locations:
    - location_id: "1-189277"
      location_name: "Molde" # Optional
    - location_id: "1-92416"
  update_frequency: 1 # Hours
```

### Configuration Options

- **pollen_types** (required): List of pollen types to track. Avaliable types:
  `Hassel`, `Or`, `Salix`, `Bjørk`, `Gress`, `Burot`

- **locations** (required): List of locations to monitor
  - **location_id** (required): YR location ID (found in the API URL)
  - **location_name** (optional): Your custom name for the location

If no 

## Finding Location IDs

Visit https://www.yr.no/nb and search for your location. The location ID is in the response URL, where the ID is located after `daglig-tabell` as such: 
`https://www.yr.no/nb/værvarsel/daglig-tabell/{locationID}/Norge/{otherNonRelevantLocationInfo}`
> Example: 
>
> `https://www.yr.no/nb/værvarsel/daglig-tabell/1-189277/Norge/M%C3%B8re%20og%20Romsdal/Molde/Molde`
> where `1-189277` is the ID. 


## Sensors Created
For each pollen type and location, the integration creates two sensors:
- `sensor.pollen_{pollen_type}_{location_name}_today` or `sensor.pollen_{pollen_type}_{region_name}_today`
- `sensor.pollen_{pollen_type}_{location_name}_tomorrow` or `sensor.pollen_{pollen_type}_{region_name}_tomorrow`

### Sensor States
- `none` - Pollen type not forecast for that day
- `low` - Low pollen level
- `moderate` - Moderate pollen level
- `high` - High pollen level
- `extreme` - Extreme pollen level

### Sensor Attributes
- `date` - Forecast date
- `region_name` - Region name fetched from the API
- `location_name` - Custom name as set in the configuration, if present
- `last_updated` - Date & time for when the sensor was last updated

## Automation Example

```yaml
automation:
  - alias: "High Pollen Alert"
    trigger:
      - platform: state
        entity_id: sensor.pollen_bjørk_molde_today
        to: "high"
      - platform: state
        entity_id: sensor.pollen_bjørk_molde_today
        to: "extreme"
    action:
      - service: notify.mobile_app_phone
        data:
          message: "High birch pollen today!"
```

## Update Interval

Data is fetched every 3 hours by default. To customize, add the `update_frequency`

## Troubleshooting

If sensors don't appear:
1. Restart Home Assistant
2. Check that location IDs are correct
3. Verify pollen type names match exactly the Norwegian names returned by the API (case-sensitive)
4. Check Home Assistant logs for errors
