from src.database import (
    add_account, get_account, list_accounts, update_account, delete_account,
    add_work, find_work_by_aweme, list_works, delete_work,
)
from src.models import Account, Work


def test_account_crud(tmp_app):
    acc = Account(nickname="张三", douyin_id="zhangsan", share_url="https://v.douyin.com/x/")
    aid = add_account(tmp_app, acc)
    assert aid > 0
    got = get_account(tmp_app, aid)
    assert got.nickname == "张三"
    assert got.douyin_id == "zhangsan"

    got.remark = "改备注"
    update_account(tmp_app, got)
    assert get_account(tmp_app, aid).remark == "改备注"

    assert len(list_accounts(tmp_app)) == 1
    delete_account(tmp_app, aid)
    assert get_account(tmp_app, aid) is None


def test_work_dedupe(tmp_app):
    acc = Account(nickname="a", douyin_id="b")
    aid = add_account(tmp_app, acc)
    w = Work(account_id=aid, aweme_id="999", work_type="视频",
             publish_time="2024", description="d", url="u")
    add_work(tmp_app, w)
    assert find_work_by_aweme(tmp_app, "999") is not None
    assert find_work_by_aweme(tmp_app, "888") is None
    assert len(list_works(tmp_app, aid)) == 1


def test_delete_account_cascade(tmp_app):
    aid = add_account(tmp_app, Account(nickname="x"))
    add_work(tmp_app, Work(account_id=aid, aweme_id="1"))
    add_work(tmp_app, Work(account_id=aid, aweme_id="2"))
    delete_account(tmp_app, aid)
    assert list_works(tmp_app, aid) == []
