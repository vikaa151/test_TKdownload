from src.douyin_client import (
    parse_work_from_detail, build_media, detect_work_type, _best_video_url, MediaItem,
)
from src.naming import build_filename


VIDEO_JSON = {
    "aweme_detail": {
        "aweme_id": "7300000000000000001",
        "desc": "测试视频 #标签",
        "create_time": 1717000000,
        "author": {
            "nickname": "测试账号",
            "unique_id": "test_douyin",
            "uid": "123456789",
            "share_info": {"share_url": "https://v.douyin.com/AbCdEf/"},
        },
        "video": {
            "bit_rate": [
                {"bit_rate": 500000, "play_addr": {"url_list": ["https://low.com/v.mp4"]}},
                {"bit_rate": 2000000, "play_addr": {"url_list": ["https://high.com/v_orig.mp4"]}},
            ],
            "download_addr": {"url_list": ["https://wm.com/v_wm.mp4"]},
            "play_addr": {"url_list": ["https://fb.com/v.mp4"]},
        },
    }
}

IMAGE_JSON = {
    "aweme_detail": {
        "aweme_id": "7300000000000000002",
        "desc": "图集描述",
        "create_time": 1717000000,
        "author": {"nickname": "图集号", "unique_id": "img_id", "uid": "2",
                   "share_info": {"share_url": "https://v.douyin.com/i/"}},
        "images": [
            {"url_list": ["https://img1.com/1.jpg"]},
            {"url_list": ["https://img2.com/2.jpg"]},
        ],
    }
}

LIVE_JSON = {
    "aweme_detail": {
        "aweme_id": "7300000000000000003",
        "desc": "实况描述",
        "create_time": 1717000000,
        "live_photo": {"img_url": "x"},
        "live_photo_status": 1,
        "author": {"nickname": "实况号", "unique_id": "live_id", "uid": "3",
                   "share_info": {"share_url": "https://v.douyin.com/l/"}},
        "video": {
            "bit_rate": [{"bit_rate": 1500000, "play_addr": {"url_list": ["https://live.com/l.mp4"]}}],
        },
    }
}


def test_parse_video_original_no_watermark():
    w = parse_work_from_detail(VIDEO_JSON, "https://v.douyin.com/x/")
    assert w.work_type == "视频"
    assert w.aweme_id == "7300000000000000001"
    assert w.description == "测试视频 #标签"
    assert w.account.nickname == "测试账号"
    assert w.account.douyin_id == "test_douyin"
    assert w.account.share_url == "https://v.douyin.com/AbCdEf/"
    assert len(w.media) == 1
    # 必须选择最高码率（原画）且不能选带水印的 download_addr
    assert w.media[0].url == "https://high.com/v_orig.mp4"
    assert w.media[0].ext == ".mp4"


def test_parse_image_multi():
    w = parse_work_from_detail(IMAGE_JSON)
    assert w.work_type == "图集"
    assert len(w.media) == 2
    assert w.media[0].url == "https://img1.com/1.jpg"
    assert w.media[0].ext == ".jpg"
    assert w.media[1].index == 1


def test_parse_live_photo_as_video():
    w = parse_work_from_detail(LIVE_JSON)
    assert w.work_type == "实况照片"
    assert len(w.media) == 1
    assert w.media[0].ext == ".mp4"
    assert w.media[0].url == "https://live.com/l.mp4"


def test_filename_integration():
    w = parse_work_from_detail(VIDEO_JSON)
    name = build_filename(w.account.remark if False else "", w.account.nickname,
                          w.account.douyin_id, w.publish_time, w.work_type, w.description)
    assert name.startswith("测试账号-test_douyin-")
    assert "视频" in name


def test_empty_detail_raises():
    import pytest
    from src.douyin_client import DouyinAPIError
    with pytest.raises(DouyinAPIError):
        parse_work_from_detail({"status_code": 0})


def test_best_video_prefers_highest_bitrate():
    video = {
        "bit_rate": [
            {"bit_rate": 300000, "play_addr": {"url_list": ["low"]}},
            {"bit_rate": 3000000, "play_addr": {"url_list": ["high"]}},
        ],
        "download_addr": {"url_list": ["wm"]},
    }
    assert _best_video_url(video) == "high"


# 真实图集常会附带一个「仅含 BGM 音频」的 video 字段，不能因此误判为视频
IMAGE_WITH_AUDIO_VIDEO_JSON = {
    "aweme_detail": {
        "aweme_id": "7300000000000000004",
        "desc": "图集带音频",
        "create_time": 1717000000,
        "author": {"nickname": "图集号2", "unique_id": "img2", "uid": "4",
                   "share_info": {"share_url": "https://v.douyin.com/i2/"}},
        "images": [
            {"url_list": ["https://img1.com/1.jpg"]},
            {"url_list": ["https://img2.com/2.jpg"]},
        ],
        "video": {
            "bit_rate": [{"bit_rate": 1500000,
                          "play_addr": {"url_list": ["https://audio.com/a.mp4"]}}],
        },
    }
}


def test_parse_album_with_audio_video_still_image():
    w = parse_work_from_detail(IMAGE_WITH_AUDIO_VIDEO_JSON)
    assert w.work_type == "图集"
    assert len(w.media) == 2
    assert all(m.ext == ".jpg" for m in w.media)
    assert w.media[0].url == "https://img1.com/1.jpg"
    assert w.media[1].index == 1


# 实况照片可能同时带有 images（静态预览帧）与 video（动态），必须一律下成视频
LIVE_WITH_IMAGES_JSON = {
    "aweme_detail": {
        "aweme_id": "7300000000000000005",
        "desc": "实况描述带图",
        "create_time": 1717000000,
        "live_photo": {"img_url": "x"},
        "live_photo_status": 1,
        "author": {"nickname": "实况号2", "unique_id": "live2", "uid": "5",
                   "share_info": {"share_url": "https://v.douyin.com/l2/"}},
        "images": [{"url_list": ["https://still.com/s.jpg"]}],
        "video": {
            "bit_rate": [{"bit_rate": 1500000,
                          "play_addr": {"url_list": ["https://live.com/motion.mp4"]}}],
        },
    }
}


def test_live_photo_always_as_video():
    w = parse_work_from_detail(LIVE_WITH_IMAGES_JSON)
    assert w.work_type == "实况照片"
    assert len(w.media) == 1
    assert w.media[0].ext == ".mp4"
    assert w.media[0].url == "https://live.com/motion.mp4"
