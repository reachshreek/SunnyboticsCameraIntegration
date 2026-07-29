from datetime import (
    datetime,
    timedelta,
    timezone,
)

from solar_metadata_tagger.gnss import (
    FixHistoryStore,
)
from solar_metadata_tagger.models import (
    GnssFix,
)
from solar_metadata_tagger.speed import (
    GnssSpeedProvider,
    SpeedSample,
)


def test_speed_sample_freshness() -> None:
    now = datetime.now(
        timezone.utc
    )

    sample = SpeedSample(
        speed_mps=0.25,
        measured_at_utc=now,
        source="test",
    )

    assert sample.valid

    assert sample.is_fresh(
        2.5,
        now + timedelta(
            seconds=1.0
        ),
    )

    assert not sample.is_fresh(
        2.5,
        now + timedelta(
            seconds=3.0
        ),
    )


def test_gnss_speed_provider_returns_latest_speed() -> None:
    store = FixHistoryStore()

    now = datetime.now(
        timezone.utc
    )

    store.update(
        GnssFix(
            latitude=37.0,
            longitude=-121.0,
            received_at_utc=now,
            speed_mps=0.25,
            source_sentence=(
                "$GPRMC,example"
            ),
        )
    )

    sample = GnssSpeedProvider(
        store
    ).sample()

    assert sample is not None
    assert sample.speed_mps == 0.25
    assert sample.source == "gnss"

    assert sample.is_fresh(
        2.5,
        now + timedelta(
            seconds=1.0
        ),
    )


def test_gnss_speed_provider_rejects_missing_speed() -> None:
    store = FixHistoryStore()

    store.update(
        GnssFix(
            latitude=37.0,
            longitude=-121.0,
            received_at_utc=datetime.now(
                timezone.utc
            ),
            speed_mps=None,
            source_sentence=(
                "$GPGGA,example"
            ),
        )
    )

    assert (
        GnssSpeedProvider(
            store
        ).sample()
        is None
    )


def test_later_gga_does_not_refresh_rmc_speed_time() -> None:
    store = FixHistoryStore()

    rmc_time = datetime(
        2026,
        7,
        15,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    later_gga_time = (
        rmc_time
        + timedelta(
            seconds=10
        )
    )

    store.update(
        GnssFix(
            latitude=37.0,
            longitude=-121.0,
            received_at_utc=rmc_time,
            speed_mps=0.20,
            source_sentence=(
                "$GPRMC,example"
            ),
        )
    )

    store.update(
        GnssFix(
            latitude=37.0,
            longitude=-121.0,
            received_at_utc=later_gga_time,
            speed_mps=0.20,
            source_sentence=(
                "$GPGGA,example"
            ),
        )
    )

    sample = GnssSpeedProvider(
        store
    ).sample()

    assert sample is not None

    assert (
        sample.measured_at_utc
        == rmc_time
    )

    assert not sample.is_fresh(
        2.5,
        later_gga_time,
    )


def test_negative_speed_is_invalid() -> None:
    sample = SpeedSample(
        speed_mps=-1.0,
        measured_at_utc=datetime.now(
            timezone.utc
        ),
        source="test",
    )

    assert not sample.valid