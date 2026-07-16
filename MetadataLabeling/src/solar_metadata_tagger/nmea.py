from __future__ import annotations

from dataclasses import dataclass
import math
from datetime import date, datetime, time, timedelta, timezone

from .errors import MetadataTaggerError
from .models import GnssFix

_KNOTS_TO_MPS = 0.514444


@dataclass
class NmeaState:
    last_date: date | None = None
    last_rmc_time: datetime | None = None
    last_altitude_m: float | None = None
    last_fix_quality: int | None = None
    last_satellites: int | None = None
    last_hdop: float | None = None
    last_speed_mps: float | None = None
    last_course_deg: float | None = None


class NmeaParser:
    """Small NMEA 0183 parser for the GGA and RMC messages used here."""

    def __init__(self) -> None:
        self.state = NmeaState()

    def parse(self, sentence: str, received_at_utc: datetime | None = None) -> GnssFix | None:
        received = received_at_utc or datetime.now(timezone.utc)
        if received.tzinfo is None:
            raise ValueError("received_at_utc must be timezone-aware")

        sentence = sentence.strip()
        if not sentence.startswith("$"):
            return None
        _validate_checksum(sentence)
        payload = sentence[1 : sentence.index("*") if "*" in sentence else None]
        fields = payload.split(",")
        message_type = fields[0][-3:]

        if message_type == "RMC":
            return self._parse_rmc(fields, sentence, received)
        if message_type == "GGA":
            return self._parse_gga(fields, sentence, received)
        return None

    def _parse_rmc(self, f: list[str], sentence: str, received: datetime) -> GnssFix | None:
        if len(f) < 10 or f[2] != "A":
            return None
        latitude = _parse_coordinate(f[3], f[4], is_latitude=True)
        longitude = _parse_coordinate(f[5], f[6], is_latitude=False)
        rmc_date = _parse_date(f[9])
        rmc_time = _parse_time(f[1])
        fix_time = datetime.combine(rmc_date, rmc_time, tzinfo=timezone.utc)
        self.state.last_date = rmc_date
        self.state.last_rmc_time = fix_time
        self.state.last_speed_mps = _float_or_none(f[7])
        if self.state.last_speed_mps is not None:
            self.state.last_speed_mps *= _KNOTS_TO_MPS
        self.state.last_course_deg = _float_or_none(f[8])
        return GnssFix(
            latitude=latitude,
            longitude=longitude,
            received_at_utc=received,
            fix_time_utc=fix_time,
            altitude_m=self.state.last_altitude_m,
            fix_quality=self.state.last_fix_quality,
            satellites=self.state.last_satellites,
            hdop=self.state.last_hdop,
            speed_mps=self.state.last_speed_mps,
            course_deg=self.state.last_course_deg,
            source_sentence=sentence,
        )

    def _parse_gga(self, f: list[str], sentence: str, received: datetime) -> GnssFix | None:
        if len(f) < 10:
            return None
        fix_quality = int(f[6] or "0")
        if fix_quality <= 0:
            return None
        latitude = _parse_coordinate(f[2], f[3], is_latitude=True)
        longitude = _parse_coordinate(f[4], f[5], is_latitude=False)
        self.state.last_fix_quality = fix_quality
        self.state.last_satellites = int(f[7]) if f[7] else None
        self.state.last_hdop = _float_or_none(f[8])
        self.state.last_altitude_m = _float_or_none(f[9])
        gga_time = _parse_time(f[1])
        basis_date = self.state.last_date or received.date()
        fix_time = datetime.combine(basis_date, gga_time, tzinfo=timezone.utc)
        # Resolve the date around UTC midnight when a GGA sentence supplies time but not date.
        delta_s = (fix_time - received.astimezone(timezone.utc)).total_seconds()
        if delta_s > 12 * 3600:
            fix_time -= timedelta(days=1)
        elif delta_s < -12 * 3600:
            fix_time += timedelta(days=1)
        return GnssFix(
            latitude=latitude,
            longitude=longitude,
            received_at_utc=received,
            fix_time_utc=fix_time,
            altitude_m=self.state.last_altitude_m,
            fix_quality=self.state.last_fix_quality,
            satellites=self.state.last_satellites,
            hdop=self.state.last_hdop,
            speed_mps=self.state.last_speed_mps,
            course_deg=self.state.last_course_deg,
            source_sentence=sentence,
        )


def _validate_checksum(sentence: str) -> None:
    if "*" not in sentence:
        return
    payload, provided = sentence[1:].split("*", 1)
    if len(provided) < 2:
        raise MetadataTaggerError("NMEA_CHECKSUM_INVALID", "NMEA checksum is incomplete.")
    checksum = 0
    for char in payload:
        checksum ^= ord(char)
    try:
        expected = int(provided[:2], 16)
    except ValueError as exc:
        raise MetadataTaggerError("NMEA_CHECKSUM_INVALID", "NMEA checksum is not hexadecimal.") from exc
    if checksum != expected:
        raise MetadataTaggerError(
            "NMEA_CHECKSUM_INVALID",
            "NMEA checksum did not match.",
            expected=f"{expected:02X}",
            calculated=f"{checksum:02X}",
        )


def _parse_coordinate(value: str, hemisphere: str, *, is_latitude: bool) -> float:
    if not value or hemisphere not in {"N", "S", "E", "W"}:
        raise MetadataTaggerError("NMEA_COORDINATE_INVALID", "NMEA coordinate is missing or invalid.")
    degree_digits = 2 if is_latitude else 3
    try:
        degrees = float(value[:degree_digits])
        minutes = float(value[degree_digits:])
    except ValueError as exc:
        raise MetadataTaggerError("NMEA_COORDINATE_INVALID", "NMEA coordinate is not numeric.") from exc
    if not math.isfinite(degrees) or not math.isfinite(minutes) or not 0.0 <= minutes < 60.0:
        raise MetadataTaggerError("NMEA_COORDINATE_INVALID", "NMEA coordinate components are invalid.")
    coordinate = degrees + minutes / 60.0
    if hemisphere in {"S", "W"}:
        coordinate = -coordinate
    limit = 90.0 if is_latitude else 180.0
    if abs(coordinate) > limit:
        raise MetadataTaggerError("NMEA_COORDINATE_INVALID", "NMEA coordinate is out of range.")
    return coordinate


def _parse_time(value: str) -> time:
    if len(value) < 6:
        raise MetadataTaggerError("NMEA_TIME_INVALID", "NMEA UTC time is missing or invalid.")
    try:
        hour = int(value[0:2])
        minute = int(value[2:4])
        second_float = float(value[4:])
        second = int(second_float)
        microsecond = int(round((second_float - second) * 1_000_000))
        if microsecond == 1_000_000:
            second += 1
            microsecond = 0
        return time(hour, minute, second, microsecond)
    except (ValueError, OverflowError) as exc:
        raise MetadataTaggerError("NMEA_TIME_INVALID", "NMEA UTC time is invalid.") from exc


def _parse_date(value: str) -> date:
    if len(value) != 6:
        raise MetadataTaggerError("NMEA_DATE_INVALID", "NMEA date is missing or invalid.")
    try:
        day = int(value[0:2])
        month = int(value[2:4])
        year_two_digits = int(value[4:6])
        year = 2000 + year_two_digits if year_two_digits < 80 else 1900 + year_two_digits
        return date(year, month, day)
    except ValueError as exc:
        raise MetadataTaggerError("NMEA_DATE_INVALID", "NMEA date is invalid.") from exc


def _float_or_none(value: str) -> float | None:
    if not value:
        return None
    try:
        result = float(value)
    except ValueError as exc:
        raise MetadataTaggerError("NMEA_NUMBER_INVALID", "NMEA numeric field is invalid.") from exc
    if not math.isfinite(result):
        raise MetadataTaggerError("NMEA_NUMBER_INVALID", "NMEA numeric field is not finite.")
    return result
