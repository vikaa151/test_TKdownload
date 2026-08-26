import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.config import AppConfig, CookieEntry, app_base_dir


def test_config_persist(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.app_base_dir", lambda: tmp_path)
    cfg = AppConfig()
    cfg.set_download_dir(str(tmp_path / "dl"), as_default=True)
    cfg.concurrency = 5
    cfg.save()
    # reload
    cfg2 = AppConfig().load()
    assert cfg2.download_dir == str(tmp_path / "dl")
    assert cfg2.concurrency == 5
    assert cfg2.save_as_default is True


def test_cookie_values(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.app_base_dir", lambda: tmp_path)
    cfg = AppConfig()
    cfg.cookies = [CookieEntry(name="A", value="ck1"), CookieEntry(name="B", value="")]
    assert cfg.cookie_values() == ["ck1"]
