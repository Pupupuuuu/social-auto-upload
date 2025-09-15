import asyncio
import configparser
import os

from playwright.async_api import async_playwright
from xhs import XhsClient

from conf import BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import tencent_logger, kuaishou_logger
from pathlib import Path
from uploader.xhs_uploader.main import sign_local


async def wait_for_login_success(page, initial_url, platform_name="平台", timeout=300):
    """
    智能检测登录成功，替换手动pause机制
    
    Args:
        page: Playwright页面对象
        initial_url: 初始登录页面URL 
        platform_name: 平台名称，用于日志输出
        timeout: 超时时间（秒）
    
    Returns:
        bool: 登录是否成功
    """
    print(f"[{platform_name}] 请在浏览器中完成登录，程序将自动检测登录状态...")
    print(f"[{platform_name}] 等待您在浏览器中登录...")
    
    login_keywords = ['login', 'signin', 'auth', 'passport', '登录', '登陆']
    start_time = asyncio.get_event_loop().time()
    
    # 快手特殊处理：检查是否已经在登录状态
    if platform_name == "快手" and "cp.kuaishou.com" in initial_url:
        print(f"[{platform_name}] 检测到快手平台，进行特殊验证...")
        # 等待用户手动确认登录
        await asyncio.sleep(5)  # 给用户时间看到提示
        print(f"[{platform_name}] 请确认您已在浏览器中完成登录，然后程序将验证登录状态...")
    
    while True:
        current_time = asyncio.get_event_loop().time()
        if current_time - start_time > timeout:
            print(f"[{platform_name}] 登录检测超时，请重试")
            return False
            
        try:
            await asyncio.sleep(2)  # 轮询间隔
            current_url = page.url
            
            # 快手特殊处理：无论URL是否变化，都检测页面元素
            if platform_name == "快手":
                try:
                    print(f"[{platform_name}] 正在检测页面元素判断登录状态...")
                    
                    # 等待页面稳定
                    await page.wait_for_load_state('networkidle', timeout=8000)
                    
                    # 首先检测未登录状态的元素（立即登录按钮）
                    login_button_count = await page.locator('text="立即登录"').count()
                    if login_button_count > 0:
                        print(f"[{platform_name}] 检测到'立即登录'按钮，仍在未登录页面，继续等待...")
                        continue
                    
                    # 检测登录后的特征元素（左侧导航栏、发布作品按钮等）
                    login_indicators = [
                        'text="首页"',           # 左侧导航的首页
                        'text="内容管理"',       # 左侧导航的内容管理  
                        'text="发布作品"',       # 顶部发布按钮
                        'text="上传视频"',       # 上传视频按钮
                        'text="继续编辑"',       # 继续编辑按钮（从截图看到的）
                        '[role="navigation"]',  # 导航栏角色
                    ]
                    
                    login_detected = False
                    for indicator in login_indicators:
                        try:
                            element_count = await page.locator(indicator).count()
                            if element_count > 0:
                                print(f"[{platform_name}] 检测到登录元素: {indicator}")
                                login_detected = True
                                break
                        except Exception:
                            continue  # 继续检测下一个元素
                    
                    if login_detected:
                        print(f"[{platform_name}] 页面元素验证成功，已登录状态!")
                        return True
                    else:
                        print(f"[{platform_name}] 未检测到登录状态元素，继续等待用户登录...")
                        # 给出操作提示
                        if (current_time - start_time) > 15 and (current_time - start_time) % 10 < 2:
                            print(f"[{platform_name}] 提示：请在浏览器中点击'立即登录'按钮并完成登录")
                        
                except Exception as e:
                    print(f"[{platform_name}] 页面元素检测异常: {e}")
                    
            else:
                # 其他平台的通用逻辑：检查URL变化
                if current_url != initial_url:
                    # 检查新URL是否不再包含登录关键词
                    is_login_page = any(keyword in current_url.lower() for keyword in login_keywords)
                    
                    if not is_login_page:
                        print(f"[{platform_name}] 检测到URL变化: {initial_url} -> {current_url}")
                        
                        # 等待页面稳定
                        try:
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            print(f"[{platform_name}] 页面加载稳定，登录检测成功!")
                            return True
                        except Exception as e:
                            print(f"[{platform_name}] 页面稳定性检查异常，但继续检测: {e}")
                            return True
                    else:
                        print(f"[{platform_name}] URL变化但仍在登录相关页面，继续等待...")
                else:
                    # 给出等待提示
                    if (current_time - start_time) > 15 and (current_time - start_time) % 10 < 2:
                        print(f"[{platform_name}] 提示：请在浏览器中完成登录操作")
            
        except Exception as e:
            print(f"[{platform_name}] 登录检测过程中出现异常: {e}")
            # 异常情况下短暂等待后继续
            await asyncio.sleep(1)

async def cookie_auth_douyin(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()
        try:
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            # 等待页面加载稳定，以便获取最终URL
            await page.wait_for_load_state('networkidle', timeout=10000)

            final_url = page.url
            print(f"[-] 抖音验证页面最终URL为: {final_url}")

            # 验证一：检查URL是否为登录页或非目标页面
            if "login" in final_url or "passport" in final_url:
                print("[+] URL中检测到登录相关路径，判定为cookie失效")
                return False
            
            # 验证二：检查是否真正到达了上传页面
            expected_url_pattern = "creator.douyin.com/creator-micro/content/upload"
            if expected_url_pattern not in final_url:
                print(f"[+] 未到达预期上传页面，当前URL: {final_url}，判定为cookie失效")
                return False

            # 验证三：保留原有逻辑，检查页面是否包含登录相关的文本
            if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
                print("[+] 页面文本中检测到登录提示，判定为cookie失效")
                return False

            print("[+] 抖音URL及页面内容验证通过，cookie有效")
            return True
        except Exception as e:
            print(f"[-] 抖音Cookie验证过程中发生异常: {e}")
            return False
        finally:
            await context.close()
            await browser.close()

async def cookie_auth_tencent(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        try:
            # 等待页面加载稳定，以便获取最终URL
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            final_url = page.url
            print(f"[-] 视频号验证页面最终URL为: {final_url}")
            
            # 验证一：检查URL是否为登录页或跳转页
            if "login" in final_url or "connect" in final_url or "authorize" in final_url:
                tencent_logger.error("[+] URL中检测到登录相关路径，判定为cookie失效")
                return False
                
            # 验证二：检查是否真正到达了发布页面
            expected_url_pattern = "channels.weixin.qq.com/platform/post/create"
            if expected_url_pattern not in final_url:
                tencent_logger.error(f"[+] 未到达预期发布页面，当前URL: {final_url}，判定为cookie失效")
                return False
            
            # 验证三：原有的元素检查逻辑
            await page.wait_for_selector('div.title-name:has-text("微信小店")', timeout=5000)  # 等待5秒
            tencent_logger.error("[+] 检测到登录提示元素，cookie失效")
            return False
        except Exception as e:
            # 如果没有检测到登录相关元素，说明cookie可能有效
            if "Timeout" in str(e) or "waiting for selector" in str(e):
                tencent_logger.success("[+] 视频号URL及页面验证通过，cookie有效")
                return True
            else:
                tencent_logger.error(f"[-] 视频号Cookie验证过程中发生异常: {e}")
                return False
        finally:
            await context.close()
            await browser.close()

async def cookie_auth_ks(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        try:
            # 等待页面加载稳定，以便获取最终URL
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            final_url = page.url
            print(f"[-] 快手验证页面最终URL为: {final_url}")
            
            # 验证一：检查URL是否为登录页或跳转页
            if "login" in final_url or "passport" in final_url or "auth" in final_url:
                kuaishou_logger.info("[+] URL中检测到登录相关路径，判定为cookie失效")
                return False
                
            # 验证二：检查是否真正到达了发布页面
            expected_url_pattern = "cp.kuaishou.com/article/publish/video"
            if expected_url_pattern not in final_url:
                kuaishou_logger.info(f"[+] 未到达预期发布页面，当前URL: {final_url}，判定为cookie失效")
                return False
            
            # 验证三：原有的元素检查逻辑
            await page.wait_for_selector("div.names div.container div.name:text('机构服务')", timeout=5000)  # 等待5秒
            kuaishou_logger.info("[+] 检测到登录提示元素，cookie失效")
            return False
        except Exception as e:
            # 如果没有检测到登录相关元素，说明cookie可能有效
            if "Timeout" in str(e) or "waiting for selector" in str(e):
                kuaishou_logger.success("[+] 快手URL及页面验证通过，cookie有效")
                return True
            else:
                kuaishou_logger.info(f"[-] 快手Cookie验证过程中发生异常: {e}")
                return False
        finally:
            await context.close()
            await browser.close()


async def cookie_auth_xhs(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.xiaohongshu.com/creator-micro/content/upload", timeout=5000)
        except Exception as e:
            print(f"[+] 小红书页面跳转异常，cookie可能失效: {e}")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True


async def check_cookie(type,file_path):
    match type:
        # 小红书
        case 1:
            return await cookie_auth_xhs(Path(BASE_DIR / "cookiesFile" / file_path))
        # 视频号
        case 2:
            return await cookie_auth_tencent(Path(BASE_DIR / "cookiesFile" / file_path))
        # 抖音
        case 3:
            return await cookie_auth_douyin(Path(BASE_DIR / "cookiesFile" / file_path))
        # 快手
        case 4:
            return await cookie_auth_ks(Path(BASE_DIR / "cookiesFile" / file_path))
        case _:
            return False

# a = asyncio.run(check_cookie(1,"3a6cfdc0-3d51-11f0-8507-44e51723d63c.json"))
# print(a)