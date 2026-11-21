"""Minimal stand-ins for the Home Assistant modules used by the integration.

They only exist so the integration code can be imported and exercised without a
Home Assistant installation. They encode our *assumptions* about the HA API, so
they catch our own mistakes (typos, wrong keys, logic) but not API changes: the
hassfest / HACS CI jobs and a real HA instance remain the reference.
"""

from __future__ import annotations

import enum
import sys
import types
from typing import Generic, TypeVar

T = TypeVar("T")


def _mod(name: str, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    parent, _, child = name.rpartition(".")
    if parent:
        setattr(sys.modules[parent], child, module)
    return module


class _Enum(str, enum.Enum):
    pass


def _str_enum(name: str, **members: str):
    return _Enum(name, members)


class _Any:
    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs


class DataUpdateCoordinator(Generic[T]):
    def __init__(self, hass, logger, *, config_entry=None, name=None, update_interval=None):
        self.hass, self.config_entry, self.name = hass, config_entry, name
        self.update_interval = update_interval
        self.data = None
        self.refresh_requests = 0

    async def async_config_entry_first_refresh(self):
        await self._async_setup()
        self.data = await self._async_update_data()

    async def async_refresh(self):
        self.data = await self._async_update_data()

    def async_set_updated_data(self, data):
        self.data = data

    async def async_request_refresh(self):
        self.refresh_requests += 1


class UpdateFailed(Exception):
    pass


class ConfigEntry(Generic[T]):
    pass


class CoordinatorEntity(Generic[T]):
    def __init__(self, coordinator):
        self.coordinator = coordinator


class ConfigFlow:
    def __init_subclass__(cls, domain=None, **kwargs):
        cls.domain = domain

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        pass

    def async_create_entry(self, *, title=None, data=None):
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, *, step_id, data_schema=None, errors=None):
        return {"type": "form", "step_id": step_id, "errors": errors or {}}

    def add_suggested_values_to_schema(self, schema, suggested):
        return schema


class OptionsFlow:
    config_entry = None

    def async_create_entry(self, *, data=None):
        return {"type": "create_entry", "data": data}

    def async_show_form(self, *, step_id, data_schema=None):
        return {"type": "form", "step_id": step_id}


class _Schema:
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, value):
        return value


class _Marker:
    def __init__(self, key, default=None, description=None):
        self.key, self.default = key, default


class _ImageEntity:
    def __init__(self, hass):
        self.hass = hass
        self._attr_image_last_updated = None
        self.state_writes = 0

    def async_write_ha_state(self):
        self.state_writes += 1

    def async_on_remove(self, fn):
        pass


def _track(hass, action, interval):
    return lambda: None


def install() -> None:
    if "homeassistant" in sys.modules:
        return
    _mod("voluptuous", Schema=_Schema, Required=_Marker, All=lambda *a: a,
         Coerce=lambda t: t, Range=lambda **k: k, Optional=_Marker, In=lambda v: v)
    _mod("homeassistant")
    _mod("homeassistant.config_entries", ConfigEntry=ConfigEntry,
         ConfigFlow=ConfigFlow, ConfigFlowResult=dict, OptionsFlow=OptionsFlow)
    _mod("homeassistant.const", CONF_HOST="host", CONF_NAME="name", CONF_PORT="port",
         Platform=_str_enum("Platform", BINARY_SENSOR="binary_sensor", BUTTON="button",
                            NUMBER="number", SELECT="select", IMAGE="image", SENSOR="sensor", SWITCH="switch"),
         EntityCategory=_str_enum("EntityCategory", CONFIG="config", DIAGNOSTIC="diagnostic"))
    _mod("homeassistant.core", HomeAssistant=type("HomeAssistant", (), {}), callback=lambda f: f,
         ServiceCall=type("ServiceCall", (), {}), ServiceResponse=dict,
         SupportsResponse=_str_enum("SupportsResponse", ONLY="only", OPTIONAL="optional"))
    _HAError = type("HomeAssistantError", (Exception,), {})
    _mod("homeassistant.exceptions", HomeAssistantError=_HAError,
         ServiceValidationError=type("ServiceValidationError", (_HAError,), {}))
    _mod("homeassistant.helpers")
    _mod("homeassistant.helpers.device_registry", DeviceInfo=dict)
    _mod("homeassistant.helpers.config_validation", config_entry_only_config_schema=lambda d: None)
    _mod("homeassistant.helpers.typing", ConfigType=dict)
    _mod("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
    _mod("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=DataUpdateCoordinator,
         UpdateFailed=UpdateFailed, CoordinatorEntity=CoordinatorEntity)
    _mod("homeassistant.helpers.selector", NumberSelector=_Any, NumberSelectorConfig=_Any,
         NumberSelectorMode=_str_enum("NumberSelectorMode", BOX="box"),
         SelectSelector=_Any, EntitySelector=_Any, EntitySelectorConfig=_Any, SelectSelectorConfig=_Any,
         SelectSelectorMode=_str_enum("SelectSelectorMode", DROPDOWN="dropdown"))
    _mod("homeassistant.components")
    _mod("homeassistant.components.sensor", SensorEntity=type("SensorEntity", (), {}),
         SensorDeviceClass=_str_enum("SensorDeviceClass", TEMPERATURE="temperature",
                                     DURATION="duration", ENUM="enum"),
         SensorStateClass=_str_enum("SensorStateClass", MEASUREMENT="measurement",
                                    TOTAL_INCREASING="total_increasing"))
    _mod("homeassistant.components.binary_sensor",
         BinarySensorEntity=type("BinarySensorEntity", (), {}),
         BinarySensorDeviceClass=_str_enum("BinarySensorDeviceClass", PROBLEM="problem",
                                           RUNNING="running"))
    _mod("homeassistant.components.image", ImageEntity=_ImageEntity)
    _mod("homeassistant.helpers.event", async_track_time_interval=_track)
    _mod("homeassistant.util")
    _mod("homeassistant.util.dt", now=lambda: __import__("datetime").datetime(2026, 11, 18, 12, 40, 5),
         utcnow=lambda: __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc))
    _mod("homeassistant.helpers.restore_state", RestoreEntity=type("RestoreEntity", (), {}))
    _mod("homeassistant.components.http", StaticPathConfig=_Any)
    _mod("homeassistant.components.frontend", add_extra_js_url=lambda hass, url: hass.js.append(url))
    _mod("homeassistant.components.switch", SwitchEntity=type("SwitchEntity", (), {}))
    _mod("homeassistant.components.button", ButtonEntity=type("ButtonEntity", (), {}))
    _mod("homeassistant.components.select", SelectEntity=type("SelectEntity", (), {}))
    _mod("homeassistant.components.number", NumberEntity=type("NumberEntity", (), {}),
         NumberDeviceClass=_str_enum("NumberDeviceClass", TEMPERATURE="temperature"),
         NumberMode=_str_enum("NumberMode", BOX="box"))
