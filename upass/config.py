"""Credential loading.

Order of precedence:
  1. Environment variables (UPASS_USERNAME, UPASS_PASSWORD, UPASS_TOTP_SECRET)
  2. A local config.json that is never committed to the repo

The secrets are excluded from __repr__ so they can't leak into logs or
tracebacks by accident.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from upass.exceptions import ConfigError

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str = field(repr=False)
    secret_key: str = field(repr=False)


def load_credentials(path: Path | str | None = None) -> Credentials:
    env = (
        os.getenv("UPASS_USERNAME"),
        os.getenv("UPASS_PASSWORD"),
        os.getenv("UPASS_TOTP_SECRET"),
    )
    if all(env):
        return Credentials(*env)  # type: ignore[arg-type]

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return Credentials(
            username=data["username"],
            password=data["password"],
            secret_key=data["secret_key"],
        )
    except FileNotFoundError as exc:
        raise ConfigError(
            f"No credentials found. Set UPASS_* env vars or create {config_path}."
        ) from exc
    except (KeyError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{config_path} is malformed: {exc}") from exc