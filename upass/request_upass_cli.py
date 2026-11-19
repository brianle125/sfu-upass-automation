"""Entry point: wires config, TOTP, browser and flow together.

Run with:
    python -m upass                    # headless Chrome
    python -m upass --browser firefox
    python -m upass --headed           # watch it run

Exit codes: 0 = requested or nothing to request, 1 = workflow failure,
2 = setup problem (credentials or browser driver).
"""
from __future__ import annotations

import argparse
import logging
import sys

from selenium import webdriver
from selenium.common.exceptions import NoSuchDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from .config import load_credentials
from .exceptions import ConfigError, UPassError
from .request_upass import RunResult, UPassFlow
from upass.totp import get_mfa  

log = logging.getLogger("upass_automation")


def build_driver(browser: str, headed: bool) -> WebDriver:
    if browser == "firefox":
        options = webdriver.FirefoxOptions()
        if not headed:
            options.add_argument("--headless")
        return webdriver.Firefox(options=options)
    if browser == "safari":  # Safari has no headless mode
        return webdriver.Safari()
    options = webdriver.ChromeOptions()
    options.add_argument("--log-level=2")
    if not headed:
        options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="upass_automation")
    parser.add_argument("--browser", choices=("chrome", "firefox", "safari"), default="chrome")
    parser.add_argument("--headed", action="store_true", help="show the browser window")
    parser.add_argument("--config", help="path to config.json (default: repo root)")
    parser.add_argument("--artifacts-dir", default="artifacts")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        credentials = load_credentials(args.config)
        driver = build_driver(args.browser, args.headed)
    except ConfigError as exc:
        log.error("%s", exc)
        return 2
    except NoSuchDriverException:
        log.error("Missing browser driver for %s.", args.browser)
        return 2

    try:
        flow = UPassFlow(
            driver,
            credentials,
            code_provider=lambda: get_mfa(credentials.secret_key),
            artifacts_dir=args.artifacts_dir,
        )
        result = flow.run()
    except UPassError as exc:
        log.error("%s: %s", type(exc).__name__, exc)
        return 1
    finally:
        driver.quit()

    log.info("Done: %s", result.value if isinstance(result, RunResult) else result)
    return 0


if __name__ == "__main__":
    sys.exit(main())