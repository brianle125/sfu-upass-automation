"""BasePage: shared browser mechanics for every page object.

Page classes (LoginPage, SfuMfaPage, UPassHomePage) inherit from this and only
expose intent-level methods like `login()` or `submit_code()`. All waiting,
retrying and failure-artifact logic lives here, so no page object ever calls
`time.sleep()` or relies on `implicitly_wait`.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

Locator = Tuple[str, str]  # e.g. (By.ID, "username")

log = logging.getLogger(__name__)


class BasePage:
    DEFAULT_TIMEOUT = 10

    def __init__(
        self,
        driver: WebDriver,
        timeout: float = DEFAULT_TIMEOUT,
        artifacts_dir: Path | str = "artifacts",
    ) -> None:
        self.driver = driver
        self.timeout = timeout
        self.artifacts_dir = Path(artifacts_dir)
        self._wait = WebDriverWait(
            driver,
            timeout,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    # ---- navigation -------------------------------------------------------

    def open(self, url: str) -> None:
        log.info("Opening %s", url)
        self.driver.get(url)

    def wait_for_url_prefix(self, prefix: str, timeout: float | None = None) -> bool:
        """Return True if the URL starts with `prefix` before the timeout."""
        try:
            WebDriverWait(self.driver, timeout or self.timeout).until(
                lambda d: d.current_url.startswith(prefix)
            )
            return True
        except TimeoutException:
            return False

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    # ---- element lookup ---------------------------------------------------

    def find_visible(self, locator: Locator) -> WebElement:
        return self._wait.until(EC.visibility_of_element_located(locator))

    def find_clickable(self, locator: Locator) -> WebElement:
        return self._wait.until(EC.element_to_be_clickable(locator))

    def is_present(self, locator: Locator, timeout: float = 2) -> bool:
        """Short, non-raising check, useful for branching (e.g. error banners)."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except TimeoutException:
            return False

    def is_enabled(self, locator: Locator) -> bool:
        return self.find_visible(locator).get_attribute("disabled") is None

    # ---- actions ----------------------------------------------------------

    def click(self, locator: Locator) -> None:
        """Click with retry on stale or intercepted elements (common flake sources)."""
        def _try_click(_driver: WebDriver) -> bool:
            try:
                self.find_clickable(locator).click()
                return True
            except (StaleElementReferenceException, ElementClickInterceptedException):
                return False

        WebDriverWait(self.driver, self.timeout).until(_try_click)

    def type_text(self, locator: Locator, text: str, clear: bool = True) -> None:
        element = self.find_visible(locator)
        if clear:
            element.clear()
        element.send_keys(text)

    def select_by_visible_text(self, locator: Locator, text: str) -> None:
        Select(self.find_visible(locator)).select_by_visible_text(text)

    # ---- iframes ----------------------------------------------------------

    def switch_to_frame(self, locator: Locator) -> None:
        self._wait.until(EC.frame_to_be_available_and_switch_to_it(locator))

    def switch_to_default(self) -> None:
        self.driver.switch_to.default_content()

    # ---- failure artifacts ------------------------------------------------

    def save_artifacts(self, label: str) -> Path:
        """Save a screenshot and page source; returns the screenshot path.

        Call this from custom exception handlers or a pytest failure hook.
        """
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = self.artifacts_dir / f"{stamp}-{label}"
        png = base.with_suffix(".png")
        self.driver.save_screenshot(str(png))
        base.with_suffix(".html").write_text(
            self.driver.page_source, encoding="utf-8"
        )
        log.error("Saved failure artifacts to %s", base)
        return png