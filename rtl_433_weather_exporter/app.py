import json
import sys
from typing import Optional

import prometheus_client
from pydantic import BaseModel
import structlog

from rtl_433_weather_exporter.settings import Settings

logger = structlog.get_logger("weather-exporter")


def unregister_python_metrics() -> None:
    # we want to prevent the prometheus client from adding unnecessary python
    # metrics by default
    prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
    prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
    prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)


def main() -> None:
    logger.info("Loading settings")
    settings = Settings()

    logger.info("Staring server", port=settings.port)
    unregister_python_metrics()
    prometheus_client.start_http_server(settings.port)

    logger.info("Staring monitor reading from stdin", port=settings.port)
    monitor = Monitor(settings=settings, stream=sys.stdin)
    monitor.run()


class Measurement(BaseModel):
    device_id: int
    model: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None


class Monitor(object):
    def __init__(self, settings: Settings, stream):
        self.settings = settings
        self.stream = stream
        self._make_gauges()

    def _make_gauges(self) -> None:
        self.temp = prometheus_client.Gauge(
            f"{self.settings.metric_basename}_temperature",
            "Temperature C",
            ["device_id", "model"],
        )
        self.humid = prometheus_client.Gauge(
            f"{self.settings.metric_basename}_humidity",
            "Humidity Percent",
            ["device_id", "model"],
        )

    def run(self) -> None:
        for line in self.stream:
            measurement = self.get_measurement(line)
            if measurement is None:
                continue

            logger.info(
                "Received measurement",
                device_id=measurement.device_id,
                model=measurement.model,
                temperature=measurement.temperature,
                humidity=measurement.humidity,
            )

            if measurement.temperature is not None:
                self.temp.labels(
                    device_id=f"{measurement.device_id}", model=f"{measurement.model}"
                ).set(measurement.temperature)

            if measurement.humidity is not None:
                self.humid.labels(
                    device_id=f"{measurement.device_id}", model=f"{measurement.model}"
                ).set(measurement.humidity)

    def get_measurement(self, line: str) -> Optional[Measurement]:
        try:
            decoded = json.loads(line.strip())

            # we arbitrarily require both ID and model
            if "id" not in decoded or "model" not in decoded:
                logger.debug("Ignoring measurement without id or model", **decoded)
                return None

            if decoded["id"] not in self.settings.allowed_ids:
                logger.debug(
                    "Ignoring measurement because id is not allowed",
                    device_id=decoded["id"],
                    allowed_ids=self.settings.allowed_ids,
                )
                return None

            temp = (
                float(decoded["temperature_C"]) if "temperature_C" in decoded else None
            )
            humidity = float(decoded["humidity"]) if "humidity" in decoded else None

            return Measurement(
                device_id=int(decoded["id"]),  # we know this one exists
                model=decoded["model"],
                temperature=temp,
                humidity=humidity,
            )

        except json.decoder.JSONDecodeError:
            logger.warning("Failed to decode json from line", line=line)
            return None
