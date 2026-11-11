import importlib.util
import json
import ssl
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "desk" / "pcuplink.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pcuplink_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_scheme_defaults_to_http_and_accepts_https():
    module = load_module()

    assert module.normalize_scheme() == "http"
    assert module.normalize_scheme(" HTTP ") == "http"
    assert module.normalize_scheme("HTTPS") == "https"


def test_normalize_scheme_rejects_unsupported_or_unsafe_values():
    module = load_module()

    for value in ("ftp", "file", "https://host", "", None, "http://user@host"):
        if value in ("", None):
            continue
        try:
            module.normalize_scheme(value)
        except ValueError:
            pass
        else:
            raise AssertionError("unsupported transport accepted: {!r}".format(value))


def test_pc_client_keeps_legacy_http_as_the_default():
    module = load_module()
    client = module.PcClient("192.0.2.10", 8420, "secret")

    assert client.scheme == "http"
    assert client._url("/stats") == "http://192.0.2.10:8420/stats"
    assert client._ssl_context is None
    assert client._https_opener is None


def test_https_client_uses_verified_tls_and_disables_redirects():
    module = load_module()
    client = module.PcClient("pc.example.test", 443, "secret", scheme="https")

    assert client._url("/stats") == "https://pc.example.test:443/stats"
    assert client._ssl_context.verify_mode == ssl.CERT_REQUIRED
    assert client._ssl_context.check_hostname is True
    assert client._https_opener is not None
    assert any(isinstance(handler, module._NoRedirectHandler)
               for handler in client._https_opener.handlers)


def test_https_get_sends_token_in_header_not_in_url():
    module = load_module()
    client = module.PcClient("pc.example.test", 443, "secret", scheme="https")
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_open(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    client._open = fake_open
    data, _elapsed = client._get("/stats")

    request = captured["request"]
    assert data == {"ok": True}
    assert request.full_url == "https://pc.example.test:443/stats"
    assert request.get_header("X-void-token") == "secret"
    assert "secret" not in request.full_url
    assert captured["timeout"] == 2.5


def test_https_post_uses_https_url_and_authenticated_header():
    module = load_module()
    client = module.PcClient("pc.example.test", 443, "secret", scheme="https")
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_open(request, timeout):
        captured["request"] = request
        return Response()

    client._open = fake_open
    result = client._post("/notify", {"title": "Hello"})

    request = captured["request"]
    assert result == {"ok": True}
    assert request.full_url == "https://pc.example.test:443/notify"
    assert request.get_header("X-void-token") == "secret"
    assert json.loads(request.data.decode("utf-8")) == {"title": "Hello"}


def test_https_redirect_handler_refuses_redirects():
    module = load_module()
    handler = module._NoRedirectHandler()

    assert handler.redirect_request(
        None, None, 302, "Found", {}, "http://other.example.test/") is None


def test_auto_discovery_remains_http_for_legacy_lan_servers(monkeypatch):
    module = load_module()
    monkeypatch.setattr(
        module, "local_subnet_hosts", lambda _ip: ["192.0.2.20"])

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"ok": true, "name": "BaseStation", "version": "4.0.0"}'

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://192.0.2.20:8420/ping"
        return Response()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    found = module.scan_for_servers("192.0.2.10", max_workers=1)

    assert len(found) == 1
    assert found[0]["host"] == "192.0.2.20"
    assert found[0]["scheme"] == "http"
