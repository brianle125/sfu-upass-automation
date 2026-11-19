from __future__ import annotations

from selenium.webdriver.common.by import By

from ..exceptions import NotEligibleError
from .base_page import BasePage


class UPassHomePage(BasePage):
    """The TransLink U-Pass BC site (institution picker + request form)."""

    URL = "https://upassbc.translink.ca"
    NO_PRIVILEGE_PATH = "/home/noprivilege"

    IDP_DROPDOWN = (By.ID, "ddlIdp")
    GO_BUTTON = (By.ID, "goButton")
    CHECKBOX = (By.ID, "chk_1")
    REQUEST_BUTTON = (By.ID, "requestButton")

    def open_home(self) -> None:
        self.open(self.URL)

    def select_institution(self, name: str) -> None:
        self.select_by_visible_text(self.IDP_DROPDOWN, name)
        self.click(self.GO_BUTTON)

    def is_no_privilege_page(self) -> bool:
        return self.current_url.rstrip("/").endswith(self.NO_PRIVILEGE_PATH)

    def can_request(self) -> bool:
        """True if the monthly request checkbox is on the page."""
        return self.is_present(self.CHECKBOX, timeout=3)

    def request_upass(self) -> None:
        self.click(self.CHECKBOX)
        if not self.is_enabled(self.REQUEST_BUTTON):
            raise NotEligibleError("Request button is disabled.")
        self.click(self.REQUEST_BUTTON)