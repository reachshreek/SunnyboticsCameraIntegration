# RUBIK Pi 3 Deployment

## Recommended filesystem layout

```text
/opt/solar-metadata-tagger/   application and virtual environment
/opt/ssd/                     WD Blue SN5000 mount point
/opt/ssd/sunnybotics/         mission data
/etc/solar-tagger/config.json robot configuration
/etc/solar-tagger/site-layout.geojson
```

The RUBIK Pi documentation notes that NVMe storage may require explicit mounting. Add the SSD to `/etc/fstab` by UUID and verify `mountpoint /opt/ssd` before enabling the service.

## Install

The included script creates the service account, virtual environment, configuration directory, and systemd unit. It intentionally does not partition or format the SSD.

```bash
sudo deploy/scripts/install_rubik_pi.sh
```

Install LUCID Arena SDK separately, then ensure `arena_api` imports inside the service virtual environment. Set the final configuration and layout before enabling startup.

```bash
sudo -u solarbot /opt/solar-metadata-tagger/.venv/bin/python -c 'import arena_api; print("Arena OK")'
sudo systemctl daemon-reload
sudo systemctl enable --now solar-capture.service
sudo systemctl status solar-capture.service
journalctl -u solar-capture.service -f
```

## Permissions

The `solarbot` account needs:

- read/write access to `/opt/ssd/sunnybotics`;
- membership in `dialout` for the NaviSys serial device;
- network access to the dedicated GigE camera interface;
- access to Arena SDK libraries.

Avoid running the capture service as root.
