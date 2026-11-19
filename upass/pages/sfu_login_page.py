from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from ..exceptions import InvalidCredentialsError
from .base_page import BasePage
from .sfu_mfa_page import SfuMfaPage


class SfuLoginPage(BasePage):
    """SFU CAS username/password form."""

    USERNAME = (By.ID, "username")
    PASSWORD = (By.ID, "password")
    SUBMIT = (By.NAME, "submit")
    ERROR_BANNER = (By.XPATH, "//div[contains(@class, 'alert alert-danger')]")

    def login(self, username: str, password: str) -> None:
        self.type_text(self.USERNAME, username)
        self.type_text(self.PASSWORD, password)
        self.click(self.SUBMIT)

        # Wait for whichever outcome appears first instead of checking for an
        # error banner immediately (which races the page load).
        self._wait.until(
            EC.any_of(
                EC.presence_of_element_located(self.ERROR_BANNER),
                EC.presence_of_element_located(SfuMfaPage.IFRAME),
            )
        )
        if self.is_present(self.ERROR_BANNER, timeout=0.5):
            raise InvalidCredentialsError("SSO rejected the username or password.")