from datetime import datetime, timezone

from solar_metadata_tagger.nmea import NmeaParser


def with_checksum(payload: str) -> str:
    checksum = 0
    for char in payload:
        checksum ^= ord(char)
    return f"${payload}*{checksum:02X}"


def test_parse_gga() -> None:
    parser = NmeaParser()
    sentence = with_checksum("GPGGA,123519.00,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,")
    received = datetime(2026, 7, 15, 12, 35, 19, tzinfo=timezone.utc)
    fix = parser.parse(sentence, received)
    assert fix is not None
    assert round(fix.latitude, 6) == 48.1173
    assert round(fix.longitude, 6) == 11.516667
    assert fix.altitude_m == 545.4
    assert fix.satellites == 8
    assert fix.fix_quality == 1


def test_parse_rmc() -> None:
    parser = NmeaParser()
    sentence = with_checksum("GPRMC,123520.00,A,4807.038,N,01131.000,E,2.0,84.4,150726,,,A")
    received = datetime(2026, 7, 15, 12, 35, 20, tzinfo=timezone.utc)
    fix = parser.parse(sentence, received)
    assert fix is not None
    assert fix.fix_time_utc == datetime(2026, 7, 15, 12, 35, 20, tzinfo=timezone.utc)
    assert round(fix.speed_mps or 0, 6) == round(2.0 * 0.514444, 6)
