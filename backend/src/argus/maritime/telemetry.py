from __future__ import annotations

import csv
import inspect
import json
import math
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from typing import cast

import httpx

from argus.compat import UTC
from argus.link.contracts import LinkTransportKind
from argus.maritime.contracts import CarrierLinkState, CarrierStatus, JsonObject

AIS_CSV_SOURCE = "ais_csv"
AIS_JSON_SOURCE = "ais_json"
CARRIER_STATUSES = {"unknown", "online", "degraded", "offline", "blocked"}
CARRIER_LINK_STATES = {
    "unknown",
    "satellite_good",
    "satellite_degraded",
    "port_wifi",
    "dark",
    "recovering",
}
CARRIER_TRANSPORT_KINDS = {"satellite", "lte", "5g", "wifi", "fiber", "ethernet", "other"}
BULK_DEGRADED_BUDGET_FLOOR_BYTES = 1_000_000

SecretResolver = Callable[[str], Mapping[str, str] | Awaitable[Mapping[str, str]]]


@dataclass(frozen=True, slots=True)
class ParseFailure:
    line_number: int
    message: str
    raw_payload: str


@dataclass(frozen=True, slots=True)
class AISPositionReading:
    mmsi: str
    latitude: float
    longitude: float
    reported_at: datetime
    raw_payload: JsonObject
    source: str = AIS_JSON_SOURCE
    speed_over_ground: float | None = None
    course_over_ground: float | None = None
    heading: float | None = None
    navigational_status: str | None = None


@dataclass(frozen=True, slots=True)
class AisCsvImportResult:
    positions: list[AISPositionReading] = field(default_factory=list)
    failures: list[ParseFailure] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class NmeaPosition:
    latitude_decimal: float
    longitude_decimal: float
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class NmeaSentenceReading:
    sentence_type: str
    values: JsonObject
    raw_sentence: str
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class NmeaReadings:
    position: NmeaPosition | None = None
    speed_over_ground: float | None = None
    course_over_ground: float | None = None
    heading: float | None = None
    sentences: list[NmeaSentenceReading] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class NmeaFileImportResult:
    readings: NmeaReadings
    failures: list[ParseFailure] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CarrierTerminalReading:
    terminal_id: str
    provider: str
    status: CarrierStatus
    link_state: CarrierLinkState
    transport_kind: LinkTransportKind | None
    last_seen_at: datetime
    raw_payload: JsonObject
    downlink_mbps: float | None = None
    uplink_mbps: float | None = None
    latency_ms: float | None = None
    packet_loss_percent: float | None = None


@dataclass(frozen=True, slots=True)
class CarrierFileImportResult:
    terminals: list[CarrierTerminalReading] = field(default_factory=list)
    failures: list[ParseFailure] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class TransferLaneDecision:
    transport: str
    defer: bool
    reason: str


class AISJsonAdapter:
    def __init__(self, *, source: str = AIS_JSON_SOURCE) -> None:
        self.source = source

    def parse(self, payload: Mapping[str, object]) -> AISPositionReading:
        mmsi = _required_text(payload, "mmsi")
        latitude = _required_float(payload, "lat", "latitude")
        longitude = _required_float(payload, "lon", "longitude")
        _validate_position(latitude=latitude, longitude=longitude)
        reported_at = _required_datetime(payload, "reported_at")
        return AISPositionReading(
            mmsi=mmsi,
            latitude=latitude,
            longitude=longitude,
            reported_at=reported_at,
            speed_over_ground=_optional_float(payload, "sog", "speed_over_ground"),
            course_over_ground=_optional_float(payload, "cog", "course_over_ground"),
            heading=_optional_float(payload, "heading"),
            navigational_status=_optional_text(payload, "navigational_status"),
            raw_payload=_json_object(payload),
            source=self.source,
        )


class AisCsvFileAdapter:
    def parse(self, csv_payload: str) -> AisCsvImportResult:
        reader = csv.DictReader(StringIO(csv_payload))
        positions: list[AISPositionReading] = []
        failures: list[ParseFailure] = []
        adapter = AISJsonAdapter(source=AIS_CSV_SOURCE)
        for line_number, row in enumerate(reader, start=2):
            raw_row = {key: value for key, value in row.items() if key is not None}
            try:
                positions.append(adapter.parse(cast(Mapping[str, object], raw_row)))
            except ValueError as exc:
                failures.append(
                    ParseFailure(
                        line_number=line_number,
                        message=str(exc),
                        raw_payload=json.dumps(raw_row, sort_keys=True),
                    )
                )
        return AisCsvImportResult(positions=positions, failures=failures)


class Nmea0183Adapter:
    def parse_lines(self, lines: Sequence[str]) -> NmeaReadings:
        position: NmeaPosition | None = None
        speed_over_ground: float | None = None
        course_over_ground: float | None = None
        heading: float | None = None
        sentences: list[NmeaSentenceReading] = []

        for line in lines:
            raw_sentence = line.strip()
            if not raw_sentence:
                continue
            sentence_payload = raw_sentence.split("*", maxsplit=1)[0]
            fields = sentence_payload.split(",")
            sentence_id = fields[0].lstrip("$").upper() if fields else ""
            sentence_type = sentence_id[-3:]
            if sentence_type == "RMC" and len(fields) >= 10:
                timestamp = _parse_nmea_datetime(fields[1], fields[9])
                latitude = _parse_nmea_coordinate(fields[3], fields[4], is_latitude=True)
                longitude = _parse_nmea_coordinate(fields[5], fields[6], is_latitude=False)
                speed_over_ground = _optional_decimal_text(fields[7])
                course_over_ground = _optional_decimal_text(fields[8])
                position = NmeaPosition(
                    latitude_decimal=latitude,
                    longitude_decimal=longitude,
                    timestamp=timestamp,
                )
                values: JsonObject = {
                    "status": fields[2],
                    "latitude": latitude,
                    "longitude": longitude,
                }
                if speed_over_ground is not None:
                    values["speed_over_ground"] = speed_over_ground
                if course_over_ground is not None:
                    values["course_over_ground"] = course_over_ground
                sentences.append(
                    NmeaSentenceReading(
                        sentence_type="RMC",
                        values=values,
                        raw_sentence=raw_sentence,
                        timestamp=timestamp,
                    )
                )
            elif sentence_type == "HDT" and len(fields) >= 2:
                heading = _optional_decimal_text(fields[1])
                sentences.append(
                    NmeaSentenceReading(
                        sentence_type="HDT",
                        values={"heading": heading} if heading is not None else {},
                        raw_sentence=raw_sentence,
                    )
                )
            else:
                sentences.append(
                    NmeaSentenceReading(
                        sentence_type=sentence_type or "UNKNOWN",
                        values={},
                        raw_sentence=raw_sentence,
                    )
                )
        return NmeaReadings(
            position=position,
            speed_over_ground=speed_over_ground,
            course_over_ground=course_over_ground,
            heading=heading,
            sentences=sentences,
        )


class Nmea0183FileAdapter:
    def parse_lines(self, lines: Sequence[str]) -> NmeaFileImportResult:
        position: NmeaPosition | None = None
        speed_over_ground: float | None = None
        course_over_ground: float | None = None
        heading: float | None = None
        sentences: list[NmeaSentenceReading] = []
        failures: list[ParseFailure] = []
        adapter = Nmea0183Adapter()
        for line_number, line in enumerate(lines, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue
            try:
                if not raw_line.startswith("$"):
                    raise ValueError("NMEA sentence must start with '$'.")
                readings = adapter.parse_lines([raw_line])
                if readings.position is not None:
                    position = readings.position
                if readings.speed_over_ground is not None:
                    speed_over_ground = readings.speed_over_ground
                if readings.course_over_ground is not None:
                    course_over_ground = readings.course_over_ground
                if readings.heading is not None:
                    heading = readings.heading
                sentences.extend(readings.sentences)
            except ValueError as exc:
                failures.append(
                    ParseFailure(
                        line_number=line_number,
                        message=str(exc),
                        raw_payload=line,
                    )
                )
        return NmeaFileImportResult(
            readings=NmeaReadings(
                position=position,
                speed_over_ground=speed_over_ground,
                course_over_ground=course_over_ground,
                heading=heading,
                sentences=sentences,
            ),
            failures=failures,
        )


class CarrierWebhookAdapter:
    def parse(self, payload: Mapping[str, object]) -> CarrierTerminalReading:
        terminal_id = _required_text(payload, "terminal_id")
        status = _carrier_status(_optional_text(payload, "status") or "unknown")
        link_state = _carrier_link_state(
            _optional_text(payload, "link_state") or _link_state_for_status(status)
        )
        transport_kind = _carrier_transport_kind(payload.get("transport_kind"))
        return CarrierTerminalReading(
            terminal_id=terminal_id,
            provider=_optional_text(payload, "provider") or "generic",
            status=status,
            link_state=link_state,
            transport_kind=transport_kind,
            downlink_mbps=_optional_float(payload, "downlink_mbps"),
            uplink_mbps=_optional_float(payload, "uplink_mbps"),
            latency_ms=_optional_float(payload, "latency_ms"),
            packet_loss_percent=_optional_float(payload, "packet_loss_percent"),
            last_seen_at=_optional_datetime(payload, "last_seen_at") or _now(),
            raw_payload=_json_object(payload),
        )


class CarrierHttpPollingAdapter:
    def __init__(
        self,
        *,
        secret_profile_id: str,
        endpoint_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.secret_profile_id = secret_profile_id
        self.endpoint_url = endpoint_url
        self.transport = transport
        self.timeout = timeout
        self.plaintext_secret: None = None

    async def poll(self, *, secret_resolver: SecretResolver) -> CarrierTerminalReading:
        resolved = secret_resolver(self.secret_profile_id)
        if inspect.isawaitable(resolved):
            resolved = await resolved
        headers = {str(key): str(value) for key, value in resolved.items()}
        async with httpx.AsyncClient(
            transport=self.transport,
            timeout=self.timeout,
            headers=headers,
        ) as client:
            response = await client.get(self.endpoint_url)
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise ValueError("Carrier polling endpoint must return a JSON object.")
        return CarrierWebhookAdapter().parse(cast(Mapping[str, object], payload))


class CarrierFileImportAdapter:
    def parse_json_lines(self, json_lines: str) -> CarrierFileImportResult:
        terminals: list[CarrierTerminalReading] = []
        failures: list[ParseFailure] = []
        adapter = CarrierWebhookAdapter()
        for line_number, line in enumerate(json_lines.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, Mapping):
                    raise ValueError("Carrier import line must be a JSON object.")
                terminals.append(adapter.parse(cast(Mapping[str, object], payload)))
            except (json.JSONDecodeError, ValueError) as exc:
                failures.append(
                    ParseFailure(
                        line_number=line_number,
                        message=str(exc),
                        raw_payload=line,
                    )
                )
        return CarrierFileImportResult(terminals=terminals, failures=failures)


def select_transfer_lane(
    *,
    link_state: str,
    terminal_status: str,
    priority_lane: str,
    remaining_budget_bytes: int,
) -> TransferLaneDecision:
    if link_state == "port_wifi" and terminal_status == "online":
        return TransferLaneDecision(
            transport="port_wifi",
            defer=False,
            reason="port_wifi_available",
        )
    if terminal_status in {"offline", "blocked"} or link_state == "dark":
        return TransferLaneDecision(
            transport="deferred",
            defer=True,
            reason="carrier_unavailable",
        )
    if link_state in {"satellite_degraded", "recovering"} or terminal_status == "degraded":
        if priority_lane == "bulk" and remaining_budget_bytes <= BULK_DEGRADED_BUDGET_FLOOR_BYTES:
            return TransferLaneDecision(
                transport="deferred",
                defer=True,
                reason="degraded_satellite_bulk_backpressure",
            )
        return TransferLaneDecision(
            transport="satellite_degraded",
            defer=False,
            reason="degraded_satellite_priority_allowed",
        )
    if link_state == "satellite_good" and terminal_status in {"online", "unknown"}:
        return TransferLaneDecision(
            transport="satellite",
            defer=False,
            reason="satellite_available",
        )
    return TransferLaneDecision(
        transport="deferred",
        defer=True,
        reason="carrier_state_unknown",
    )


def _transport_kind_for_link_state(link_state: CarrierLinkState) -> LinkTransportKind:
    if link_state in {"satellite_good", "satellite_degraded", "recovering"}:
        return "satellite"
    if link_state == "port_wifi":
        return "wifi"
    return "other"


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required field: {key}")
    return str(value)


def _optional_text(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None or str(value).strip() == "":
        return None
    return str(value)


def _required_float(payload: Mapping[str, object], *keys: str) -> float:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip() != "":
            return _coerce_float(value)
    raise ValueError(f"Missing required field: {keys[0]}")


def _optional_float(payload: Mapping[str, object], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip() != "":
            return _coerce_float(value)
    return None


def _coerce_float(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("Numeric field cannot be boolean.")
    if isinstance(value, int | float | str):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("Numeric field must be finite.")
        return parsed
    raise ValueError("Numeric field must be a number or numeric string.")


def _required_datetime(payload: Mapping[str, object], key: str) -> datetime:
    value = _optional_datetime(payload, key)
    if value is None:
        raise ValueError(f"Missing required field: {key}")
    return value


def _optional_datetime(payload: Mapping[str, object], key: str) -> datetime | None:
    value = payload.get(key)
    if value is None or isinstance(value, datetime):
        return value
    if str(value).strip() == "":
        return None
    return _parse_iso_datetime(str(value))


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _parse_nmea_datetime(time_value: str, date_value: str) -> datetime | None:
    if not time_value or not date_value or len(date_value) != 6:
        return None
    hour = int(time_value[0:2])
    minute = int(time_value[2:4])
    second = int(_coerce_float(time_value[4:]))
    day = int(date_value[0:2])
    month = int(date_value[2:4])
    year_suffix = int(date_value[4:6])
    year = 1900 + year_suffix if year_suffix >= 80 else 2000 + year_suffix
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


def _parse_nmea_coordinate(value: str, hemisphere: str, *, is_latitude: bool) -> float:
    if not value:
        raise ValueError("Missing NMEA coordinate.")
    degree_width = 2 if is_latitude else 3
    degrees = int(value[:degree_width])
    minutes = _coerce_float(value[degree_width:])
    decimal = degrees + minutes / 60
    if hemisphere.upper() in {"S", "W"}:
        decimal *= -1
    return decimal


def _optional_decimal_text(value: str) -> float | None:
    if not value:
        return None
    return _coerce_float(value)


def _validate_position(*, latitude: float, longitude: float) -> None:
    if latitude < -90 or latitude > 90:
        raise ValueError("latitude must be between -90 and 90.")
    if longitude < -180 or longitude > 180:
        raise ValueError("longitude must be between -180 and 180.")


def _carrier_status(value: str) -> CarrierStatus:
    if value not in CARRIER_STATUSES:
        raise ValueError(f"Invalid carrier status: {value}")
    return cast(CarrierStatus, value)


def _carrier_link_state(value: str) -> CarrierLinkState:
    if value not in CARRIER_LINK_STATES:
        raise ValueError(f"Invalid carrier link_state: {value}")
    return cast(CarrierLinkState, value)


def _carrier_transport_kind(value: object) -> LinkTransportKind | None:
    if value is None or str(value).strip() == "":
        return None
    normalized = str(value).strip().lower()
    if normalized not in CARRIER_TRANSPORT_KINDS:
        return "other"
    return cast(LinkTransportKind, normalized)


def _link_state_for_status(status: CarrierStatus) -> CarrierLinkState:
    if status == "online":
        return "satellite_good"
    if status == "degraded":
        return "satellite_degraded"
    if status in {"offline", "blocked"}:
        return "dark"
    return "unknown"


def _json_object(value: Mapping[str, object]) -> JsonObject:
    return {str(key): item for key, item in value.items()}


def _now() -> datetime:
    return datetime.now(tz=UTC)
