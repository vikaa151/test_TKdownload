from src.config import AppConfig, app_base_dir
from src.database import init_db, list_accounts, list_works, find_work_by_aweme
from src.tasks import save_and_download, dedupe_check, derive_account_homepage, upsert_account
from src.douyin_client import ParsedWork, ParsedAccount, MediaItem
from src.logger import setup_logger
from pathlib import Path


class FakeClient:
    def __init__(self):
        self.saved = []

    def download_media(self, media, dest_dir, filename_base, cookie=""):
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        paths = []
        for i, m in enumerate(media):
            suffix = f"_{i+1}" if len(media) > 1 else ""
            p = Path(dest_dir) / f"{filename_base}{suffix}{m.ext}"
            p.write_bytes(b"fake-bytes")
            paths.append(str(p))
        self.saved = paths
        return paths


def _sample_work(aweme_id="7300000000000000001", desc="desc"):
    return ParsedWork(
        aweme_id=aweme_id, work_type="视频", publish_time="2024-01-01 12.00.00",
        description=desc, url="https://v.douyin.com/x/",
        media=[MediaItem(url="https://x/v.mp4", ext=".mp4")],
        account=ParsedAccount(nickname="张三", douyin_id="zhangsan", uid="123",
                              share_url="https://v.douyin.com/s/"),
    )


def test_save_and_download_creates_account_and_work(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.app_base_dir", lambda: tmp_path)
    cfg = AppConfig()
    init_db(cfg)
    cfg.set_download_dir(str(tmp_path / "dl"))
    setup_logger(cfg)
    client = FakeClient()

    res = save_and_download(cfg, client, _sample_work(), remark="我的备注")
    assert res.get("ok") is True
    accs = list_accounts(cfg)
    assert len(accs) == 1
    assert accs[0].nickname == "张三"
    assert accs[0].share_url == "https://v.douyin.com/s/"
    works = list_works(cfg)
    assert len(works) == 1
    assert works[0].remark == "我的备注"
    # 文件名符合规范：备注-昵称-抖音号-时间-类型-描述
    assert works[0].file_name.startswith("我的备注-张三-zhangsan-2024-01-01 12.00.00-视频-desc")
    # 文件确实落盘
    assert Path(works[0].local_path).exists()


def test_dedupe_skip(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.app_base_dir", lambda: tmp_path)
    cfg = AppConfig()
    init_db(cfg)
    cfg.set_download_dir(str(tmp_path / "dl"))
    setup_logger(cfg)
    client = FakeClient()
    save_and_download(cfg, client, _sample_work())
    assert dedupe_check(cfg, "7300000000000000001") is True
    # 非强制重复下载 -> 跳过
    res = save_and_download(cfg, client, _sample_work(), force=False)
    assert res.get("skipped") is True
    # 强制 -> 再次写入（唯一约束会冲突，应被忽略或更新）
    res2 = save_and_download(cfg, client, _sample_work(), force=True)
    assert res2.get("ok") is True or res2.get("skipped") is True


def _sample_image_work(aweme_id="7300000000000000999", count=3):
    return ParsedWork(
        aweme_id=aweme_id, work_type="图集", publish_time="2024-02-02 10.00.00",
        description="图集描述", url="https://v.douyin.com/y/",
        media=[MediaItem(url=f"https://x/{i}.jpg", ext=".jpg") for i in range(count)],
        account=ParsedAccount(nickname="张三", douyin_id="zhangsan", uid="123",
                              share_url="https://v.douyin.com/s/"),
    )


def _setup_cfg(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.app_base_dir", lambda: tmp_path)
    cfg = AppConfig()
    init_db(cfg)
    cfg.set_download_dir(str(tmp_path / "dl"))
    setup_logger(cfg)
    return cfg


def test_rule_single_video_in_root(tmp_path, monkeypatch):
    # 规则4：单视频直接放默认下载路径根目录，不建文件夹
    cfg = _setup_cfg(tmp_path, monkeypatch)
    save_and_download(cfg, FakeClient(), _sample_work(), merge=False)
    base = Path(cfg.download_dir)
    assert not (base / "张三_zhangsan_作品数量共1个").exists()
    assert len(list(base.glob("*.mp4"))) == 1
    w = list_works(cfg)[0]
    assert Path(w.local_path) == base


def test_rule_image_set_uses_picture_folder(tmp_path, monkeypatch):
    # 规则3：图集独立建「图片数量共x个」文件夹
    cfg = _setup_cfg(tmp_path, monkeypatch)
    save_and_download(cfg, FakeClient(), _sample_image_work(count=3), merge=False)
    base = Path(cfg.download_dir)
    folder = base / "张三_zhangsan_图片数量共3个"
    assert folder.is_dir()
    assert len(list(folder.glob("*.jpg"))) == 3
    w = list_works(cfg)[0]
    assert w.local_path == str(folder)


def test_rule_batch_multi_video_consolidate(tmp_path, monkeypatch):
    # 规则1：批量同账号多视频合并到「作品数量共2个」
    cfg = _setup_cfg(tmp_path, monkeypatch)
    save_and_download(cfg, FakeClient(), _sample_work(aweme_id="111"), merge=True)
    save_and_download(cfg, FakeClient(), _sample_work(aweme_id="222", desc="another"), merge=True)
    base = Path(cfg.download_dir)
    folder = base / "张三_zhangsan_作品数量共2个"
    assert folder.is_dir()
    assert len(list(folder.glob("*.mp4"))) == 2
    for w in list_works(cfg):
        assert w.local_path == str(folder)


def test_rule_cross_time_merge_moves_files(tmp_path, monkeypatch):
    # 规则2：跨时间（先单视频，再第二视频触发合并）文件被移动到统一文件夹
    cfg = _setup_cfg(tmp_path, monkeypatch)
    save_and_download(cfg, FakeClient(), _sample_work(aweme_id="111"), merge=False)
    base = Path(cfg.download_dir)
    assert len(list(base.glob("*.mp4"))) == 1
    save_and_download(cfg, FakeClient(), _sample_work(aweme_id="222", desc="another"), merge=True)
    folder = base / "张三_zhangsan_作品数量共2个"
    assert folder.is_dir()
    assert len(list(folder.glob("*.mp4"))) == 2
    # 根目录不再残留视频文件
    assert len(list(base.glob("*.mp4"))) == 0


def test_rule_consolidate_image_and_video(tmp_path, monkeypatch):
    # 混合：图集(图片文件夹) + 视频 -> 合并到「作品数量共2个」
    cfg = _setup_cfg(tmp_path, monkeypatch)
    save_and_download(cfg, FakeClient(), _sample_image_work(count=2), merge=False)
    save_and_download(cfg, FakeClient(), _sample_work(aweme_id="222"), merge=True)
    base = Path(cfg.download_dir)
    folder = base / "张三_zhangsan_作品数量共2个"
    assert folder.is_dir()
    assert len(list(folder.glob("*.jpg"))) == 2
    assert len(list(folder.glob("*.mp4"))) == 1


def test_derive_account_homepage():
    # sec_uid 最可靠；缺失时退化到 douyin_id / uid
    from src.models import Account
    a1 = Account(nickname="x", sec_uid="SEC123")
    assert derive_account_homepage(a1) == "https://www.douyin.com/user/SEC123"
    a2 = Account(nickname="x", douyin_id="did_99")
    assert derive_account_homepage(a2) == "https://www.douyin.com/user/did_99"
    a3 = Account(nickname="x", uid="12345")
    assert derive_account_homepage(a3) == "https://www.douyin.com/user/12345"
    a4 = Account(nickname="x")
    assert derive_account_homepage(a4) == ""


def test_upsert_account_autofills_homepage(tmp_path, monkeypatch):
    # 解析时 API 未返回 share_url，但仍应按 sec_uid 自动补全主页链接
    cfg = _setup_cfg(tmp_path, monkeypatch)
    parsed = ParsedWork(
        aweme_id="999", work_type="视频", publish_time="2024-01-01 12.00.00",
        description="d", url="https://v.douyin.com/x/",
        media=[MediaItem(url="https://x/v.mp4", ext=".mp4")],
        account=ParsedAccount(nickname="李四", douyin_id="lisi", uid="456",
                              sec_uid="SEC999", share_url="", homepage_url=""),
    )
    acc = upsert_account(cfg, parsed)
    assert acc.share_url == "https://www.douyin.com/user/SEC999"
    assert acc.homepage_url == "https://www.douyin.com/user/SEC999"
