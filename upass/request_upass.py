"""Orchestration layer.

Page objects know *how* to drive each screen. This module knows *what order*
to do things in and what to do when something goes wrong (retry policy,
failure artifacts). Keeping the two apart means the retry logic can be unit
tested with a fake code provider and a no-op sleep, no browser required.
"""
from __future__ import annotations

import logging
import time
from enum import Enum
from pathlib import Path
from typing import Callable

from selenium.webdriver.remote.webdriver import WebDriver

from .config import Credentials
from upass.exceptions import MfaFailedError, NoPrivilegeError, UPassError
from upass.pages import SfuMfaPage, SfuLoginPage, UPassHomePage

log = logging.getLogger(__name__)


class RunResult(Enum):
    REQUESTED = "requested"
    NOT_AVAILABLE = "not_available"  # outside the monthly request window


class UPassFlow:
    SFU_IDP = "Simon Fraser University"
    TOTP_STEP_SECONDS = 30

    def __init__(
        self,
        driver: WebDriver,
        credentials: Credentials,
        code_provider: Callable[[], str],
        *,
        max_mfa_attempts: int = 3,
        artifacts_dir: Path | str = "artifacts",
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.credentials = credentials
        self.code_provider = code_provider
        self.max_mfa_attempts = max_mfa_attempts
        self._sleep = sleep

        self.home = UPassHomePage(driver, artifacts_dir=artifacts_dir)
        self.login_page = SfuLoginPage(driver, artifacts_dir=artifacts_dir)
        self.mfa_page = SfuMfaPage(driver, artifacts_dir=artifacts_dir)

    def run(self) -> RunResult:
        try:
            return self._run()
        except UPassError as exc:
            self._capture_failure(type(exc).__name__)
            raise

    # ---- internals --------------------------------------------------------

    def _run(self) -> RunResult:
        log.info("Opening U-Pass BC")
        self.home.open_home()
        self.home.select_institution(self.SFU_IDP)

        log.info("Logging into SFU")
        self.login_page.login(self.credentials.username, self.credentials.password)

        self._complete_mfa()

        if self.home.is_no_privilege_page():
            raise NoPrivilegeError(
                "U-Pass site rejected access: the site may be down, or your "
                "institution has not enabled U-Pass for you."
            )

        if not self.home.can_request():
            log.info("Nothing to request right now (window opens on the 16th).")
            return RunResult.NOT_AVAILABLE

        log.info("Requesting U-Pass")
        self.home.request_upass()
        log.info("U-Pass requested")
        return RunResult.REQUESTED

    def _complete_mfa(self) -> None:
        for attempt in range(1, self.max_mfa_attempts + 1):
            if attempt > 1:
                # A TOTP code is single-use, so retrying immediately would
                # submit the same rejected code. Wait for the next window.
                self._wait_for_next_totp_window()

            log.info("Submitting MFA code (attempt %d/%d)", attempt, self.max_mfa_attempts)
            self.mfa_page.submit_code(self.code_provider())

            if self.mfa_page.wait_for_url_prefix(UPassHomePage.URL):
                log.info("MFA accepted")
                return
            log.warning("MFA not accepted")

        raise MfaFailedError(f"MFA failed after {self.max_mfa_attempts} attempts.")

    def _wait_for_next_totp_window(self) -> None:
        remaining = self.TOTP_STEP_SECONDS - (time.time() % self.TOTP_STEP_SECONDS)
        self._sleep(remaining + 1)

    def _capture_failure(self, label: str) -> None:
        try:
            self.home.save_artifacts(label)
        except Exception:  # never let artifact capture mask the real error
            log.exception("Could not save failure artifacts")