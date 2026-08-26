from src.naming import build_filename, sanitize, format_time
from datetime import datetime


def test_sanitize_removes_illegal():
    assert sanitize('a/b:c*?"') == "a_b_c___"
    assert sanitize("  hello   world ") == "hello world"
    assert sanitize("a\tb") == "a_b"


def test_build_filename_full():
    name = build_filename("我的备注", "张三", "zhangsan", "2024-01-01 12.00.00",
                           "视频", "今天天气真好")
    assert name == "我的备注-张三-zhangsan-2024-01-01 12.00.00-视频-今天天气真好"


def test_build_filename_empty_remark_omits_prefix():
    name = build_filename("", "张三", "zhangsan", "2024-01-01 12.00.00", "图集", "描述")
    assert name == "张三-zhangsan-2024-01-01 12.00.00-图集-描述"
    assert not name.startswith("-")


def test_build_filename_truncates_long_desc():
    long_desc = "字" * 200
    name = build_filename("", "昵", "id", "t", "视频", long_desc)
    assert "…" in name
    assert len(name) <= 180


def test_build_filename_collapses_empty_parts():
    name = build_filename("", "", "", "", "", "")
    assert name == "未命名作品"


def test_format_time_no_colon():
    dt = datetime(2024, 1, 1, 12, 30, 5)
    assert format_time(dt) == "2024-01-01 12.30.05"
    assert ":" not in format_time(dt)
    assert format_time(dt, with_colon=True) == "2024-01-01 12:30:05"


def test_build_account_folder_name():
    from src.naming import build_account_folder_name
    # 规则1/2：多作品 -> 作品数量共x个
    assert build_account_folder_name("张三", "zhangsan", "works", 2) == "张三_zhangsan_作品数量共2个"
    # 规则3：图集 -> 图片数量共x个
    assert build_account_folder_name("李四", "lisi", "images", 5) == "李四_lisi_图片数量共5个"
    # 空昵称/抖音号兜底
    folder = build_account_folder_name("", "", "works", 1)
    assert "未命名" in folder and "na" in folder
