import json
import os
from typing import Any, Callable
import pytest

from rtl_433_weather_exporter.settings import Settings


@pytest.fixture()
def env_mocker(request) -> Callable[[str, str], None]:
    original_values = {}

    def env_replacer(key: str, value: str) -> None:
        original_values[key] = os.getenv(key)
        os.environ[key] = value

    def undo_env() -> None:
        for k, v in original_values.items():
            if v is None:
                del os.environ[k]
            else:
                os.environ[k] = v

    request.addfinalizer(undo_env)

    return env_replacer


def describe_Settings():
    def defaults():
        s = Settings()
        assert s.port == 9100
        assert s.allowed_ids == set()
        assert s.metric_basename == "rtl433_weather_probe"

    @pytest.mark.parametrize("port", [9300, 1234])
    @pytest.mark.parametrize("allowed_ids", ["[1,2,3]", "[5, 5, 5]"])
    @pytest.mark.parametrize("metric_basename", ["foo", "bar"])
    def env_overrides(port: int, allowed_ids: str, metric_basename: str, env_mocker):
        env_mocker("RTL_EXP_PORT", str(port))
        env_mocker("RTL_EXP_ALLOWED_IDS", allowed_ids)
        env_mocker("RTL_EXP_METRIC_BASENAME", metric_basename)

        s = Settings()
        assert s.port == port
        assert s.allowed_ids == set(json.loads(allowed_ids))
        assert s.metric_basename == metric_basename
