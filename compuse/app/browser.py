"""Browser engine that drives a real (headed) Chrome via Playwright.

The engine is imported lazily so the frozen .exe only requires Playwright when
``run`` is used. Installed Chrome (channel="chrome") is reused instead of
downloading a bundled browser. Only well-known, low-ambiguity selectors are
performed; every step is wrapped in a permit by the sequence runner.
"""
from __future__ import annotations

from typing import Any

from compuse.protocol import WebOp


class BrowserError(RuntimeError):
    pass


def _as_browser_error(exc: Exception, action: str) -> BrowserError:
    if isinstance(exc, BrowserError):
        return exc
    return BrowserError(f"{action} failed: {exc}")


class BrowserEngine:
    def __init__(self, *, headed: bool = True, channel: str = "chrome",
                 navigation_timeout_ms: int = 30000) -> None:
        self.headed = headed
        self.channel = channel
        self.navigation_timeout_ms = navigation_timeout_ms
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise BrowserError("Playwright is not installed; run `pip install playwright`") from exc
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                channel=self.channel, headless=not self.headed)
            self._page = self._browser.new_page()
            self._page.set_default_timeout(self.navigation_timeout_ms)
        except Exception as exc:
            self.close()
            raise BrowserError(f"could not launch {self.channel}: {exc}") from exc

    @property
    def page(self):
        if self._page is None:
            raise BrowserError("browser not started")
        return self._page

    def goto(self, url: str) -> dict[str, Any]:
        if not str(url).startswith(("http://", "https://")):
            raise BrowserError("goto requires an absolute http(s) url")
        try:
            self.page.goto(url, wait_until="domcontentloaded",
                           timeout=self.navigation_timeout_ms)
        except Exception as exc:
            raise _as_browser_error(exc, f"goto {url}") from exc
        return {"performed": True, "detail": f"navigated to {url}",
                "title": self.page.title(), "url": self.page.url}

    def click(self, selector: str) -> dict[str, Any]:
        if not selector:
            raise BrowserError("click requires a CSS selector")
        try:
            before = self.page.url
            target = self.page.locator(selector).first
            target.click(timeout=self.navigation_timeout_ms)
            if self.page.url != before:
                self.page.wait_for_load_state("domcontentloaded",
                                              timeout=self.navigation_timeout_ms)
        except Exception as exc:
            raise _as_browser_error(exc, f"click {selector}") from exc
        return {"performed": True, "detail": f"clicked {selector}",
                "url": self.page.url}

    def type(self, selector: str, text: str) -> dict[str, Any]:
        if not selector:
            raise BrowserError("type requires a CSS selector")
        try:
            self.page.locator(selector).first.fill(text,
                                                   timeout=self.navigation_timeout_ms)
        except Exception as exc:
            raise _as_browser_error(exc, f"type into {selector}") from exc
        return {"performed": True, "detail": f"typed into {selector}"}

    def wait(self, seconds: float) -> dict[str, Any]:
        self.page.wait_for_timeout(int(seconds * 1000))
        return {"performed": True, "detail": f"waited {seconds}s"}

    def run_webop(self, action: WebOp) -> dict[str, Any]:
        op = action.op
        if op == "goto":
            return self.goto(action.url or "")
        if op == "click":
            return self.click(action.selector or "")
        if op == "type":
            return self.type(action.selector or "", action.text or "")
        if op == "wait":
            return self.wait(action.seconds)
        raise BrowserError(f"unknown web op: {op}")

    def close(self) -> None:
        try:
            if self._browser is not None:
                self._browser.close()
            if self._playwright is not None:
                self._playwright.stop()
        finally:
            self._browser = None
            self._playwright = None
            self._page = None

    def __enter__(self) -> "BrowserEngine":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()


__all__ = ["BrowserEngine", "BrowserError"]