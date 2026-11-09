from desk.syncthing import (
    DEFAULT_MUOS_URL,
    config_candidates,
    discover_connection,
    read_connection,
)


def test_muos_config_candidate_is_found(tmp_path):
    storage = tmp_path / "MUOS"
    cfg = storage / "syncthing" / "config.xml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        "<configuration><gui enabled='true'>"
        "<address>127.0.0.1:7070</address>"
        "<apikey>secret-api-key</apikey>"
        "</gui></configuration>",
        encoding="utf-8",
    )
    found = discover_connection(
        storage_roots=[str(storage)],
        app_roots=[],
        home=tmp_path / "home",
    )
    assert found is not None
    assert found["url"] == "http://127.0.0.1:7070"
    assert found["key"] == "secret-api-key"
    assert found["config"] == str(cfg)


def test_muos_default_port_and_wildcard_address(tmp_path):
    cfg = tmp_path / "config.xml"
    cfg.write_text(
        "<configuration><gui><address>0.0.0.0:7070</address>"
        "<apikey>abc</apikey></gui></configuration>",
        encoding="utf-8",
    )
    found = read_connection(cfg)
    assert found["url"] == DEFAULT_MUOS_URL
    assert found["key"] == "abc"


def test_syncthing_config_rejects_missing_or_invalid_api_key(tmp_path):
    cfg = tmp_path / "config.xml"
    cfg.write_text(
        "<configuration><gui><address>127.0.0.1:7070</address>"
        "</gui></configuration>",
        encoding="utf-8",
    )
    assert read_connection(cfg) is None
    cfg.write_text("not xml", encoding="utf-8")
    assert read_connection(cfg) is None


def test_api_txt_fallback(tmp_path):
    cfg = tmp_path / "config.xml"
    cfg.write_text(
        "<configuration><gui><address>:7070</address>"
        "</gui></configuration>",
        encoding="utf-8",
    )
    (tmp_path / "api.txt").write_text("file-key\n", encoding="utf-8")
    found = read_connection(cfg)
    assert found["url"] == DEFAULT_MUOS_URL
    assert found["key"] == "file-key"
