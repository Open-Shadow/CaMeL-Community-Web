"""
通用工具函数
"""

import random
import string
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.utils import timezone


# =============================================================================
# 日期时间格式化
# =============================================================================

def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """
    格式化日期时间

    Args:
        dt: 日期时间对象
        fmt: 格式化字符串

    Returns:
        格式化后的字符串
    """
    if not dt:
        return ""
    return dt.strftime(fmt)


def format_datetime_human(dt: datetime) -> str:
    """
    人性化日期时间显示

    示例: "刚刚", "5分钟前", "2小时前", "昨天", "3天前", "2024-01-15"
    """
    if not dt:
        return ""

    # 确保是带时区的 datetime
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)

    now = timezone.now()
    diff = now - dt

    if diff.days < 0:
        return "未来"

    if diff.days == 0:
        seconds = diff.seconds
        if seconds < 60:
            return "刚刚"
        if seconds < 3600:
            return f"{seconds // 60}分钟前"
        return f"{seconds // 3600}小时前"

    if diff.days == 1:
        return "昨天"

    if diff.days < 7:
        return f"{diff.days}天前"

    if diff.days < 30:
        return f"{diff.days // 7}周前"

    return dt.strftime("%Y-%m-%d")


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """格式化日期"""
    if not dt:
        return ""
    return dt.strftime(fmt)


# =============================================================================
# 金额格式化
# =============================================================================

def format_currency(amount: Decimal | float | int, symbol: str = "$") -> str:
    """
    格式化金额显示（统一显示 $x.xx）

    Args:
        amount: 金额数值
        symbol: 货币符号

    Returns:
        格式化后的金额字符串，如 "$1.50"
    """
    if amount is None:
        amount = 0

    decimal_amount = Decimal(str(amount)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return f"{symbol}{decimal_amount:.2f}"


def parse_currency(currency_str: str) -> Decimal:
    """
    从货币字符串解析金额

    Args:
        currency_str: 如 "$1.50" 或 "1.50"

    Returns:
        Decimal 金额
    """
    cleaned = currency_str.replace("$", "").replace(",", "").strip()
    return Decimal(cleaned)


def round_amount(amount: Decimal | float | int) -> Decimal:
    """
    四舍五入金额到两位小数

    Args:
        amount: 金额数值

    Returns:
        四舍五入后的 Decimal
    """
    return Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# 文本处理
# =============================================================================

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度（包含后缀）
        suffix: 截断后添加的后缀

    Returns:
        截断后的文本
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    truncated_length = max_length - len(suffix)
    if truncated_length <= 0:
        return suffix[:max_length]

    return text[:truncated_length] + suffix


def truncate_html(html: str, max_length: int, suffix: str = "...") -> str:
    """
    截断 HTML 文本（移除标签后截断）

    Args:
        html: HTML 文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        纯文本截断结果
    """
    import re

    if not html:
        return ""

    # 移除 HTML 标签
    text = re.sub(r"<[^>]+>", "", html)
    # 移除多余空白
    text = re.sub(r"\s+", " ", text).strip()

    return truncate_text(text, max_length, suffix)


def generate_slug(text: str, max_length: int = 50) -> str:
    """
    将文本转换为 URL 友好的 slug

    Args:
        text: 原始文本
        max_length: 最大长度

    Returns:
        slug 字符串
    """
    import re

    if not text:
        return ""

    # 转换为小写
    slug = text.lower()
    # 保留中文、英文、数字
    slug = re.sub(r"[^\w\u4e00-\u9fff]", "-", slug)
    # 移除连续的 -
    slug = re.sub(r"-+", "-", slug)
    # 移除首尾 -
    slug = slug.strip("-")
    # 截取长度
    return slug[:max_length]


def mask_string(text: str, start: int = 2, end: int = 2, mask: str = "*") -> str:
    """
    遮盖字符串中间部分

    Args:
        text: 原始文本
        start: 开头保留字符数
        end: 结尾保留字符数
        mask: 遮盖字符

    Returns:
        遮盖后的文本，如 "ab***cd"
    """
    if not text:
        return ""

    length = len(text)
    if length <= start + end:
        return mask * length

    return text[:start] + mask * (length - start - end) + text[-end:]


# =============================================================================
# 随机生成
# =============================================================================

def generate_random_string(length: int = 8, chars: Optional[str] = None) -> str:
    """
    生成随机字符串

    Args:
        length: 字符串长度
        chars: 使用的字符集，默认大小写字母+数字

    Returns:
        随机字符串
    """
    if chars is None:
        chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def generate_numeric_code(length: int = 6) -> str:
    """
    生成纯数字验证码

    Args:
        length: 验证码长度

    Returns:
        数字字符串
    """
    return "".join(random.choices(string.digits, k=length))


def generate_unique_id(prefix: str = "", length: int = 12) -> str:
    """
    生成唯一 ID（基于时间戳 + 随机数）

    Args:
        prefix: ID 前缀
        length: 随机部分长度

    Returns:
        唯一 ID 字符串
    """
    import time

    timestamp = int(time.time() * 1000)
    random_part = generate_random_string(length, string.ascii_lowercase + string.digits)
    return f"{prefix}{timestamp}{random_part}"


# =============================================================================
# 缓存键生成
# =============================================================================

def make_cache_key(prefix: str, *parts: str) -> str:
    """
    生成缓存键

    Args:
        prefix: 键前缀
        parts: 键组成部分

    Returns:
        格式化的缓存键，如 "prefix:part1:part2"
    """
    if parts:
        return f"{prefix}:{':'.join(str(p) for p in parts)}"
    return prefix


def make_cache_key_from_obj(prefix: str, obj, *attrs: str) -> str:
    """
    从对象属性生成缓存键

    Args:
        prefix: 键前缀
        obj: 对象
        attrs: 属性名列表

    Returns:
        缓存键
    """
    parts = [getattr(obj, attr, "") for attr in attrs]
    return make_cache_key(prefix, *parts)


# =============================================================================
# 数值处理
# =============================================================================

def clamp(value: int | float, min_value: int | float, max_value: int | float) -> int | float:
    """
    将数值限制在指定范围内

    Args:
        value: 原始值
        min_value: 最小值
        max_value: 最大值

    Returns:
        限制后的值
    """
    return max(min_value, min(value, max_value))


def calculate_percentage(part: float, total: float, decimals: int = 2) -> float:
    """
    计算百分比

    Args:
        part: 部分值
        total: 总计值
        decimals: 小数位数

    Returns:
        百分比数值
    """
    if total == 0:
        return 0.0
    percentage = (part / total) * 100
    return round(percentage, decimals)


# =============================================================================
# 安全相关
# =============================================================================

def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除危险字符

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    import re

    if not filename:
        return "unnamed"

    # 移除路径分隔符和危险字符
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    # 限制长度
    if len(filename) > 100:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:96] + (f".{ext}" if ext else "")

    return filename


def is_safe_password(password: str) -> tuple[bool, str]:
    """
    检查密码安全性

    Returns:
        (是否安全, 错误信息)
    """
    if len(password) < 8:
        return False, "密码至少需要8个字符"

    if not any(c.isupper() for c in password):
        return False, "密码需要包含大写字母"

    if not any(c.islower() for c in password):
        return False, "密码需要包含小写字母"

    if not any(c.isdigit() for c in password):
        return False, "密码需要包含数字"

    return True, ""
