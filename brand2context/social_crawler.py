"""Step 3.5: 社交媒体抓取 - 使用 MediaCrawler 抓取微博、小红书、抖音数据。"""

import json
import os
import subprocess
import time
import glob
from datetime import datetime
from typing import Optional

from .config import MEDIACRAWLER_PATH, SOCIAL_PLATFORMS, SOCIAL_CRAWL_TIMEOUT


def crawl_social_media(
    brand_name: str, platforms: Optional[list[str]] = None
) -> list[dict]:
    """
    抓取社交媒体数据。

    Args:
        brand_name: 品牌名称，用于搜索关键词
        platforms: 要抓取的平台列表，默认使用配置中的 SOCIAL_PLATFORMS

    Returns:
        统一格式的社交媒体数据列表
    """
    if not brand_name:
        print("⚠️ 未提供品牌名称，跳过社交媒体抓取")
        return []

    if platforms is None:
        platforms = SOCIAL_PLATFORMS

    # 检查 MediaCrawler 是否存在
    if not os.path.exists(MEDIACRAWLER_PATH):
        print(f"⏭️ 跳过社交媒体抓取（MediaCrawler 不存在: {MEDIACRAWLER_PATH}）")
        return []

    print(f"📱 开始社交媒体抓取，品牌: {brand_name}，平台: {platforms}")

    all_results = []

    for platform in platforms:
        platform_name_map = {"wb": "weibo", "xhs": "xiaohongshu", "dy": "douyin"}
        platform_display = platform_name_map.get(platform, platform)
        print(f"   🔍 正在抓取 {platform_display}...")

        try:
            results = _crawl_single_platform(platform, brand_name)
            print(f"   ✅ {platform_display} 抓取完成，获得 {len(results)} 条数据")
            all_results.extend(results)
        except Exception as e:
            print(f"   ❌ {platform_display} 抓取失败: {e}")
            continue

        # 等待2-3秒，避免触发反爬
        time.sleep(2.5)

    print(f"📱 社交媒体抓取完成，总计 {len(all_results)} 条数据")
    return all_results


def _crawl_single_platform(platform: str, brand_name: str) -> list[dict]:
    """
    抓取单个平台的数据。

    Args:
        platform: 平台标识 (wb/xhs/dy)
        brand_name: 品牌名称

    Returns:
        该平台的数据列表
    """
    env = os.environ.copy()
    env["DISPLAY"] = os.environ.get("DISPLAY", ":99")
    if "XAUTHORITY" in env:
        del env["XAUTHORITY"]

    cmd = [
        "cd",
        MEDIACRAWLER_PATH,
        "&&",
        "uv",
        "run",
        "python",
        "main.py",
        "--platform",
        platform,
        "--type",
        "search",
        "--keywords",
        brand_name,
        "--headless",
        "true",
        "--get_comment",
        "false",
        "--save_data_option",
        "jsonl",
        "--max_concurrency_num",
        "1",
    ]

    cmd_str = f'cd {MEDIACRAWLER_PATH} && uv run python main.py --platform {platform} --type search --keywords "{brand_name}" --headless true --get_comment false --save_data_option jsonl --max_concurrency_num 1'

    try:
        result = subprocess.run(
            cmd_str,
            shell=True,
            env=env,
            timeout=SOCIAL_CRAWL_TIMEOUT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"      MediaCrawler stderr: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        print(f"      抓取超时 ({SOCIAL_CRAWL_TIMEOUT}秒)")
        raise
    except Exception as e:
        print(f"      执行命令失败: {e}")
        raise

    # 读取输出的 JSONL 文件
    jsonl_path = os.path.join(
        MEDIACRAWLER_PATH, "data", platform, "jsonl", "search_contents_*.jsonl"
    )
    jsonl_files = glob.glob(jsonl_path)

    if not jsonl_files:
        print(f"      未找到 JSONL 文件: {jsonl_path}")
        return []

    # 取最新的文件
    latest_file = max(jsonl_files, key=os.path.getmtime)
    print(f"      读取文件: {latest_file}")

    results = []
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    mapped = _map_platform_record(platform, record)
                    if mapped:
                        results.append(mapped)
                except json.JSONDecodeError as e:
                    print(f"      解析 JSON 行失败: {e}")
                    continue
    except Exception as e:
        print(f"      读取文件失败: {e}")
        raise

    return results


def _map_platform_record(platform: str, record: dict) -> Optional[dict]:
    """
    将各平台原始记录映射为统一格式。

    Args:
        platform: 平台标识
        record: 原始记录字典

    Returns:
        统一格式的字典，若映射失败返回 None
    """
    try:
        if platform == "wb":
            # 微博字段映射
            content = record.get("content", "")
            return {
                "platform": "weibo",
                "title": content[:50] if content else "",
                "content": content,
                "url": record.get("note_url", ""),
                "author": record.get("user", {}).get("name", "")
                if isinstance(record.get("user"), dict)
                else "",
                "likes": int(record.get("liked_count", 0) or 0),
                "comments": int(record.get("comments_count", 0) or 0),
                "shares": int(record.get("shared_count", 0) or 0),
                "created_at": _parse_weibo_time(record.get("created_at", "")),
                "tags": record.get("tags", []) or [],
            }

        elif platform == "xhs":
            # 小红书字段映射
            display_title = record.get("display_title") or record.get("title", "")
            desc = record.get("desc", "")
            liked_count = record.get("liked_count", 0) or 0
            comment_count = record.get("comment_count", 0) or 0
            share_count = (
                record.get("share_count") or record.get("shared_count", 0) or 0
            )

            return {
                "platform": "xiaohongshu",
                "title": display_title,
                "content": desc,
                "url": record.get("note_url", "") or record.get("share_url", ""),
                "author": record.get("nickname", "") or record.get("author", ""),
                "likes": int(liked_count),
                "comments": int(comment_count),
                "shares": int(share_count),
                "created_at": record.get("time", "") or record.get("created_at", ""),
                "tags": record.get("tags", []) or record.get("topics", []) or [],
            }

        elif platform == "dy":
            # 抖音字段映射
            title = record.get("title", "")
            desc = record.get("desc", "") or record.get("text", "")

            return {
                "platform": "douyin",
                "title": title or desc[:50],
                "content": desc or title,
                "url": record.get("share_url", "") or record.get("url", ""),
                "author": record.get("nickname", "") or record.get("author", ""),
                "likes": int(record.get("digg_count", 0) or 0),
                "comments": int(record.get("comment_count", 0) or 0),
                "shares": int(record.get("share_count", 0) or 0),
                "created_at": record.get("create_time", "")
                or record.get("created_at", ""),
                "tags": record.get("tags", []) or record.get("challenges", []) or [],
            }

        else:
            print(f"      未知平台: {platform}")
            return None

    except Exception as e:
        print(f"      映射记录失败: {e}")
        return None


def _parse_weibo_time(time_str: str) -> str:
    """
    解析微博时间字符串为 ISO 格式。

    Args:
        time_str: 微博时间字符串

    Returns:
        ISO 格式时间字符串
    """
    if not time_str:
        return ""

    # 微博时间格式通常是: Tue Mar 25 15:30:00 +0800 2025
    # 尝试多种格式
    formats = [
        "%a %b %d %H:%M:%S %z %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.isoformat()
        except ValueError:
            continue

    # 如果解析失败，返回原始字符串
    return time_str
