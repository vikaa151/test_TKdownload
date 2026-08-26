import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.config import AppConfig, app_base_dir, CookieEntry
from src.database import add_account, list_accounts, init_db
from src.config_io import export_config, import_config, read_config_json_in_zip
from src.models import Account


def test_config_export_import_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.app_base_dir", lambda: tmp_path)
    cfg = AppConfig()
    init_db(cfg)
    cfg.cookies = [CookieEntry(name="A", value="secret_ck")]
    cfg.save()
    add_account(cfg, Account(nickname="导出账号", douyin_id="exp"))

    zip_path = tmp_path / "backup.zip"
    export_config(cfg, zip_path)
    assert zip_path.exists()

    # 在另一个目录导入还原
    dst = tmp_path / "restore"
    dst.mkdir()
    monkeypatch.setattr("src.config.app_base_dir", lambda: dst)
    cfg2 = AppConfig()
    init_db(cfg2)
    import_config(cfg2, zip_path)
    accs = list_accounts(cfg2)
    assert len(accs) == 1
    assert accs[0].nickname == "导出账号"
    # Cookie 也应被还原
    assert any(c.value == "secret_ck" for c in cfg2.cookies)
