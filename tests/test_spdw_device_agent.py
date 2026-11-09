import importlib.util
import json
import os
import re
import stat
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "service" / "spdw_hub" / "device_agent.py"


def load_agent_module():
    spec = importlib.util.spec_from_file_location("spdw_device_agent_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    return urllib.request.urlopen(req, timeout=4)


def expect_http_error(url, method="GET", data=None, headers=None, code=401):
    try:
        request(url, method=method, data=data, headers=headers)
    except urllib.error.HTTPError as exc:
        assert exc.code == code
        return exc
    raise AssertionError("expected HTTP {}".format(code))


def start_agent(tmp_path):
    module = load_agent_module()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index.html").write_text("<html>SPDW</html>", encoding="utf-8")
    data = tmp_path / "data"
    agent = module.DeviceAgent(data, assets, host="127.0.0.1", port=0)
    assert agent.start() is True
    port = agent.httpd.server_address[1]
    return module, agent, "http://127.0.0.1:{}".format(port)


def login(base_url, pin):
    body = urllib.parse.urlencode({"pin": pin}).encode("utf-8")
    with request(base_url + "/api/login", method="POST", data=body,
                 headers={"Content-Type": "application/x-www-form-urlencoded"}) as response:
        result = json.loads(response.read().decode("utf-8"))
        cookie = response.headers.get("Set-Cookie").split(";", 1)[0]
    return cookie, result["csrf_token"]


def test_device_agent_generates_private_pairing_pin(tmp_path):
    module = load_agent_module()
    assets = tmp_path / "assets"
    assets.mkdir()
    agent = module.DeviceAgent(tmp_path / "data", assets, host="127.0.0.1", port=0)

    assert re.fullmatch(r"\d{8}", agent.pairing_pin)
    security = tmp_path / "data" / "spdw_hub" / "device_agent.json"
    assert json.loads(security.read_text(encoding="utf-8"))["pairing_pin"] == agent.pairing_pin
    if os.name == "posix":
        assert stat.S_IMODE(security.stat().st_mode) == 0o600


def test_device_agent_requires_pairing_before_file_api_and_csrf_for_writes(tmp_path):
    _module, agent, base = start_agent(tmp_path)
    try:
        expect_http_error(base + "/api/list?area=in&path=")

        cookie, csrf = login(base, agent.pairing_pin)
        headers = {"Cookie": cookie}
        expect_http_error(
            base + "/api/mkdir",
            method="POST",
            data=urllib.parse.urlencode({"area": "in", "path": "", "name": "blocked"}).encode(),
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
            code=403,
        )

        body = urllib.parse.urlencode({
            "area": "in", "path": "", "name": "safe-folder"
        }).encode("utf-8")
        with request(base + "/api/mkdir", method="POST", data=body, headers={
            **headers, "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": csrf,
        }) as response:
            assert json.loads(response.read().decode("utf-8"))["ok"] is True

        with request(base + "/api/list?area=in&path=", headers=headers) as response:
            entries = json.loads(response.read().decode("utf-8"))["entries"]
        assert any(item["name"] == "safe-folder" and item["type"] == "dir"
                   for item in entries)
    finally:
        agent.stop()


def test_device_agent_rejects_symlink_escape_from_file_area(tmp_path):
    module, agent, _base = start_agent(tmp_path)
    try:
        outside = tmp_path / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        link = tmp_path / "data" / "incoming" / "escape.txt"
        link.symlink_to(outside)

        try:
            agent._resolve("in", "escape.txt", must_exist=True)
        except module.AgentError as exc:
            assert "escapes" in str(exc)
        else:
            raise AssertionError("symlink outside the managed area must be blocked")
    finally:
        agent.stop()


def test_device_agent_uploads_without_overwriting_existing_files(tmp_path):
    _module, agent, base = start_agent(tmp_path)
    try:
        cookie, csrf = login(base, agent.pairing_pin)
        boundary = "spdw-test-boundary"
        content = b"hello handheld\\r\\n"
        payload = (
            b"--" + boundary.encode() + b"\r\n"
            b'Content-Disposition: form-data; name="file"; filename="notes.txt"\r\n'
            b"Content-Type: text/plain\r\n\r\n" + content +
            b"\r\n--" + boundary.encode() + b"--\r\n"
        )
        headers = {
            "Cookie": cookie,
            "X-CSRF-Token": csrf,
            "Content-Type": "multipart/form-data; boundary=" + boundary,
        }
        with request(base + "/api/upload?area=in&path=", method="POST",
                     data=payload, headers=headers) as response:
            result = json.loads(response.read().decode("utf-8"))
            assert result["ok"] is True
        target = tmp_path / "data" / "incoming" / "notes.txt"
        assert target.read_bytes() == content

        expect_http_error(base + "/api/upload?area=in&path=", method="POST",
                          data=payload, headers=headers, code=409)
    finally:
        agent.stop()


def test_device_agent_health_page_is_public_but_file_content_is_not(tmp_path):
    _module, agent, base = start_agent(tmp_path)
    try:
        with request(base + "/api/health") as response:
            health = json.loads(response.read().decode("utf-8"))
        assert health["name"] == "SPDW Device Agent"
        assert "pairing_pin" not in health

        with request(base + "/") as response:
            page = response.read().decode("utf-8")
        assert "SPDW" in page

        expect_http_error(base + "/api/read?area=in&path=anything")
    finally:
        agent.stop()

def test_multipart_parser_preserves_binary_trailing_newlines(tmp_path):
    _module, agent, _base = start_agent(tmp_path)
    try:
        handler = agent.make_handler()
        boundary = b"spdw-binary-boundary"
        payload = (
            b"--" + boundary + b"\r\n"
            b'Content-Disposition: form-data; name="file"; filename="capture.bin"\r\n'
            b"Content-Type: application/octet-stream\r\n\r\n"
            b"\x00\x01payload\r\n"
            b"--" + boundary + b"--\r\n"
        )
        filename, data = handler._parse_multipart(payload, boundary)
        assert filename == "capture.bin"
        assert data == b"\x00\x01payload\r\n"
    finally:
        agent.stop()
