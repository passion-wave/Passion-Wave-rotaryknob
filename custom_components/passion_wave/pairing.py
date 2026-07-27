"""Secure first-use pairing for PassionWave ESPHome endpoints."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
import os
from typing import Any

from aioesphomeapi import APIClient, APIConnectionError
from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.components.esphome.encryption_key_storage import (
    async_get_encryption_key_storage,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr

from .const import (
    BRIDGE_PROJECT_NAME,
    ESPHOME_API_PORT,
    S3_PROJECT_NAME,
)

ESPHOME_SERVICE_TYPE = "_esphomelib._tcp.local."
# ESPHome reserves the all-zero PSK for the bounded first-use provisioning
# channel. The session still uses an ephemeral Noise handshake, but does not
# authenticate the peer until the generated device key has been installed.
ZERO_NOISE_PSK = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
SUPPORTED_PROJECTS = {S3_PROJECT_NAME, BRIDGE_PROJECT_NAME}


@dataclass(frozen=True, slots=True)
class DiscoveredEndpoint:
    """One PassionWave processor announced over ESPHome mDNS."""

    host: str
    port: int
    project_name: str
    friendly_name: str
    mac_address: str


class PairingError(Exception):
    """Base error for a secure endpoint pairing failure."""


class ProvisioningWindowClosed(PairingError):
    """The endpoint no longer accepts first-use provisioning."""


class UnexpectedEndpoint(PairingError):
    """The selected host is not the expected PassionWave processor."""


def _decode_property(value: bytes | str | None) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value or ""


async def async_discover_endpoints(
    hass: HomeAssistant, timeout: float = 2.5
) -> list[DiscoveredEndpoint]:
    """Discover supported PassionWave endpoints on the local network."""
    zc = await zeroconf.async_get_instance(hass)
    endpoints: dict[tuple[str, str], DiscoveredEndpoint] = {}
    pending: set[asyncio.Task[None]] = set()

    async def resolve(service_type: str, name: str) -> None:
        info = AsyncServiceInfo(service_type, name)
        if not await info.async_request(zc, 3000):
            return
        properties = info.properties
        project_name = _decode_property(properties.get(b"project_name"))
        if project_name not in SUPPORTED_PROJECTS or not info.server:
            return
        mac_address = _decode_property(properties.get(b"mac"))
        if not mac_address:
            return
        host = info.server.removesuffix(".")
        friendly_name = (
            _decode_property(properties.get(b"friendly_name"))
            or name.removesuffix(f".{service_type}")
        )
        endpoints[(project_name, host)] = DiscoveredEndpoint(
            host=host,
            port=info.port or ESPHOME_API_PORT,
            project_name=project_name,
            friendly_name=friendly_name,
            mac_address=mac_address,
        )

    def on_service_state_change(
        zeroconf: Any,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        del zeroconf
        if state_change is ServiceStateChange.Removed:
            return
        task = hass.async_create_task(resolve(service_type, name))
        pending.add(task)
        task.add_done_callback(pending.discard)

    browser = AsyncServiceBrowser(
        zc, ESPHOME_SERVICE_TYPE, handlers=[on_service_state_change]
    )
    try:
        await asyncio.sleep(timeout)
        if pending:
            await asyncio.gather(*tuple(pending), return_exceptions=True)
    finally:
        await browser.async_cancel()
    return sorted(
        endpoints.values(), key=lambda item: (item.project_name, item.friendly_name)
    )


def _existing_esphome_entry(
    hass: HomeAssistant, mac_address: str
) -> config_entries.ConfigEntry | None:
    normalized_mac = dr.format_mac(mac_address)
    return hass.config_entries.async_entry_for_domain_unique_id(
        "esphome", normalized_mac
    )


def endpoint_is_configured(
    hass: HomeAssistant, endpoint: DiscoveredEndpoint
) -> bool:
    """Return whether Home Assistant already owns this endpoint's key."""
    return _existing_esphome_entry(hass, endpoint.mac_address) is not None


async def _abort_pending_esphome_flow(
    hass: HomeAssistant, mac_address: str
) -> None:
    normalized_mac = dr.format_mac(mac_address)
    for progress in hass.config_entries.flow.async_progress_by_handler(
        "esphome", include_uninitialized=True
    ):
        if progress.get("context", {}).get("unique_id") == normalized_mac:
            hass.config_entries.flow.async_abort(progress["flow_id"])


async def async_secure_pair_endpoint(
    hass: HomeAssistant,
    endpoint: DiscoveredEndpoint,
    expected_project: str,
) -> config_entries.ConfigEntry:
    """Install a random key and create the matching ESPHome config entry."""
    if existing := _existing_esphome_entry(hass, endpoint.mac_address):
        return existing

    zc = await zeroconf.async_get_instance(hass)
    client = APIClient(
        endpoint.host,
        endpoint.port,
        "",
        zeroconf_instance=zc,
        noise_psk=ZERO_NOISE_PSK,
    )
    try:
        await client.connect()
        info = await client.device_info()
        if info.project_name != expected_project:
            raise UnexpectedEndpoint(
                f"Expected {expected_project}, got {info.project_name or 'unknown'}"
            )
        if existing := _existing_esphome_entry(hass, info.mac_address):
            return existing

        encoded_key = base64.b64encode(os.urandom(32))
        key = encoded_key.decode()
        key_storage = await async_get_encryption_key_storage(hass)
        # Store first: if the device accepts the key but the response or the
        # following config flow is interrupted, ESPHome discovery can recover
        # the exact key instead of locking the customer out.
        await key_storage.async_store_key(info.mac_address, key)
        if not await client.noise_encryption_set_key(encoded_key):
            await key_storage.async_remove_key(info.mac_address)
            raise ProvisioningWindowClosed(endpoint.host)
        mac_address = info.mac_address
    except APIConnectionError as err:
        raise ProvisioningWindowClosed(endpoint.host) from err
    finally:
        await client.disconnect()

    # A discovery flow may already be showing Home Assistant's manual key
    # prompt. Replace only the flow for this exact MAC, then drive the official
    # ESPHome config flow with the newly installed key.
    await _abort_pending_esphome_flow(hass, mac_address)
    result = await hass.config_entries.flow.async_init(
        "esphome",
        context={"source": config_entries.SOURCE_USER},
        data={CONF_HOST: endpoint.host, CONF_PORT: endpoint.port},
    )
    if result["type"] is FlowResultType.FORM:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"noise_psk": key}
        )
    if result["type"] is not FlowResultType.CREATE_ENTRY:
        raise PairingError(
            f"ESPHome setup ended with {result['type']} at {result.get('step_id')}"
        )
    entry = result["result"]
    if not isinstance(entry, config_entries.ConfigEntry):
        raise PairingError("ESPHome did not return a config entry")
    return entry
