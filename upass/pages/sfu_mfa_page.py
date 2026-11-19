from __future__ import annotations

from selenium.webdriver.common.by import By

from .base_page import BasePage


class SfuMfaPage(BasePage):
    """The Duo MFA prompt, rendered inside an iframe."""

    IFRAME = (By.ID, "duo_iframe")
    CODE_INPUT = (By.ID, "code")
    SUBMIT = (By.XPATH, "//button[contains(@class, 'ui primary button')]")

    def submit_code(self, code: str) -> None:
        # Always return to the top-level document, even on failure, so a retry
        # can locate the iframe again. (The original script stayed inside the
        # frame, so its second loop iteration could never find it.)
        self.switch_to_frame(self.IFRAME)
        try:
            self.type_text(self.CODE_INPUT, code)
            self.click(self.SUBMIT)
        finally:
            self.switch_to_default()