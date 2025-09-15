# 导入 Python 标准库
import asyncio
import configparser
import time
from pathlib import Path

from xhs import XhsClient

# 导入工具函数和配置
from conf import BASE_DIR
# 导入每个平台的上传工具
from uploader.bilibili_uploader.main import read_cookie_json_file, extract_keys_from_json, random_emoji, BilibiliUploader
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
from uploader.ks_uploader.main import ks_setup, KSVideo
from uploader.tencent_uploader.main import weixin_setup, TencentVideo
from uploader.xhs_uploader.main import sign_local, beauty_print
from utils.constant import VideoZoneTypes, TencentZoneTypes

config = configparser.RawConfigParser()
config.read(Path(BASE_DIR / "uploader" / "xhs_uploader" / "accounts.ini"))


# ==========================
# 逻辑块：Bilibili 上传
# ==========================
def upload_to_bilibili(file, title, tags):
    # how to get cookie, see the file of get_bilibili_cookie.py.
    account_file = Path(BASE_DIR / "cookies" / "bilibili_uploader" / "account.json")
    if not account_file.exists():
        print(f"{account_file.name} 配置文件不存在")
        return  # 退出函数，相当于原脚本的 exit()
    cookie_data = read_cookie_json_file(account_file)
    cookie_data = extract_keys_from_json(cookie_data)

    tid = VideoZoneTypes.SPORTS_FOOTBALL.value  # 设置分区id

    # just avoid error, bilibili don't allow same title of video.
    title += random_emoji()

    # 打印视频文件名、标题和 hashtag
    # 视频文件名：C:\Users\Missi\Framework\social - auto - upload - main\videos\demo.mp4
    # 标题：这位勇敢的男子为了心爱之人每天坚守 🥺❤️‍🩹🍋
    # Hashtag：['坚持不懈', '爱情执着', '奋斗使者', '短视频']
    print(f"视频文件名：{file}")
    print(f"标题：{title}")
    print(f"Hashtag：{tags}")

    # I set desc same as title, do what u like.
    desc = title

    bili_uploader = BilibiliUploader(cookie_data, file, title, desc, tid, tags, None)
    bili_uploader.upload()

    # life is beautiful don't so rush. be kind be patience
    time.sleep(30)


# ==========================
# 逻辑块：XHS（小红书）上传
# ==========================
def upload_to_xhs(file, title, tags):
    config = configparser.RawConfigParser()
    config.read(Path(BASE_DIR / "uploader" / "xhs_uploader" / "accounts.ini"))
    cookies = config.get('account1', 'cookies')
    xhs_client = XhsClient(cookies, sign=sign_local, timeout=60)

    try:
        xhs_client.get_video_first_frame_image_id("3214")
    except:
        print("cookie 失效")
        return  # 退出函数，相当于原脚本的 exit()

    # 加入到标题 补充标题（xhs 可以填1000字不写白不写）
    tags_str = ' '.join(['#' + tag for tag in tags])
    hash_tags = []

    # 打印视频文件名、标题和 hashtag
    # 视频文件名：C:\Users\Missi\Framework\social - auto - upload - main\videos\demo.mp4
    # 标题：这位勇敢的男子为了心爱之人每天坚守 🥺❤️‍🩹
    # Hashtag：['坚持不懈', '爱情执着', '奋斗使者', '短视频']
    print(f"视频文件名：{file}")
    print(f"标题：{title}")
    print(f"Hashtag：{tags}")

    topics = []
    # 获取hashtag
    for i in tags[:3]:
        topic_official = xhs_client.get_suggest_topic(i)
        if topic_official:
            topic_official[0]['type'] = 'topic'
            topic_one = topic_official[0]
            hash_tag_name = topic_one['name']
            hash_tags.append(hash_tag_name)
            topics.append(topic_one)

    hash_tags_str = ' ' + ' '.join(['#' + tag + '[话题]#' for tag in hash_tags])
    note = xhs_client.create_video_note(title=title[:20], video_path=str(file),
                                        desc=title + tags_str + hash_tags_str,
                                        topics=topics,
                                        is_private=False,
                                        post_time=None)

    beauty_print(note)
    # 强制休眠30s，避免风控（必要）
    time.sleep(30)


# ==========================
# 逻辑块：Tencent 上传
# ==========================
def upload_to_tencent(file, title, tags):
    # 获取 cookie 文件
    account_file = Path(BASE_DIR / "cookies" / "tencent_uploader" / "account.json")

    # 获取 cookie , 如果cookie失效那么就弹窗重新登陆
    asyncio.run(weixin_setup(account_file, handle=True))

    category = TencentZoneTypes.LIFESTYLE.value  # 标记原创需要否则不需要传

    # 打印视频文件名、标题和 hashtag
    print(f"视频文件名：{file}")
    print(f"标题：{title}")
    print(f"Hashtag：{tags}")
    app = TencentVideo(title, file, tags, 0, account_file, category)
    asyncio.run(app.main(), debug=False)


# ==========================
# 逻辑块：Douyin 上传
# ==========================
def upload_to_douyin(file, title, tags):
    # 获取cookie
    account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / "account.json")
    # 验证cookie
    cookie_setup = asyncio.run(douyin_setup(account_file, handle=False))

    # 获取封面图
    thumbnail_path = file.with_suffix('.png')

    # 打印ビデ文件名、标题和 hashtag
    print(f"视频文件名：{file}")
    print(f"标题：{title}")
    print(f"Hashtag：{tags}")

    # 暂时没有时间修复封面上传，故先隐藏掉该功能
    # if thumbnail_path.exists():
    # app = DouYinVideo(title, file, tags, publish_datetimes[index], account_file, thumbnail_path=thumbnail_path)
    # else:
    app = DouYinVideo(title, file, tags, 0, account_file)
    asyncio.run(app.main(), debug=False)


# ==========================
# 逻辑块：Kuaishou 上传
# ==========================
# 函数：上传视频到 Kuaishou
# 直接复制 upload_video_to_kuaishou.py 的逻辑，未做任何修改
def upload_to_kuaishou(file, title, tags):
    # 获取cookie
    account_file = Path(BASE_DIR / "cookies" / "ks_uploader" / "account.json")
    # 验证cookie
    cookie_setup = asyncio.run(ks_setup(account_file, handle=False))

    # 打印视频文件名、标题和 hashtag
    print(f"视频文件名：{file}")
    print(f"标题：{title}")
    print(f"Hashtag：{tags}")

    app = KSVideo(title, file, tags, 0, account_file)
    asyncio.run(app.main(), debug=False)


# ==========================
# 逻辑块：程序主入口
# ==========================
# 这是程序的起点，按顺序调用五个平台的上传函数
if __name__ == '__main__':
    print("=== 开始一键上传到所有平台 ===")
    file = Path(r"C:\Users\Missi\Framework\social-auto-upload\videos\demo.mp4")
    title = "这位勇敢的男子为了心爱之人每天坚守 🥺❤️‍🩹🍋"
    tags = ['坚持不懈', '爱情执着', '奋斗使者', '短视频']

    # 调用 Bilibili 上传
    # print("\n=== Bilibili ===")
    # upload_to_bilibili(file=file, title=title, tags=tags)

    # 调用 XHS 上传
    # print("\n=== XHS ===")
    # upload_to_xhs(file=file, title=title, tags=tags)

    # # 调用 Tencent 上传
    # print("\n=== Tencent ===")
    # upload_to_tencent(file=file, title=title, tags=tags)

    # # 调用 Douyin 上传
    # print("\n=== Douyin ===")
    # upload_to_douyin(file=file, title=title, tags=tags)

    # # 调用 Kuaishou 上传
    # print("\n=== Kuaishou ===")
    # upload_to_kuaishou(file=file, title=title, tags=tags)

    # 所有上传完成
    print("\n=== 所有平台上传完成！ ===")
