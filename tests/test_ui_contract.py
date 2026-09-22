"""Catch missing controls and broken navigation when the static layout changes."""
from html.parser import HTMLParser
import re

import httpx
import pytest


class Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.anchors = []
        self.lang = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.anchors.append(attrs["href"][1:])
        if tag == "html":
            self.lang = attrs.get("lang")


@pytest.mark.asyncio
async def test_ui_controls_and_navigation_remain_connected(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        page = await client.get("/")
        script = await client.get("/static/app.js")
        css = await client.get("/static/styles.css")
    controls = Controls()
    controls.feed(page.text)
    assert controls.lang == "en"
    assert len(controls.ids) == len(set(controls.ids)), "Duplicate control IDs"
    assert set(controls.anchors) <= set(controls.ids)
    script_controls = set(re.findall(r"\$\('([^']+)'\)", script.text))
    assert script_controls <= set(controls.ids), "JavaScript references a missing control"
    assert controls.ids.index("model-configs") < controls.ids.index("rule-form")
    assert controls.ids.index("playground-request") < controls.ids.index("playground-output")
    assert "color-scheme: dark" in css.text
