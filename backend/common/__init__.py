"""
通用工具模块
"""

# 导出常用常量
from .constants import (
    # 信用等级
    CreditLevel,
    CreditLevelConfig,
    # 价格范围
    MIN_SKILL_PRICE,
    MAX_SKILL_PRICE,
    MIN_BOUNTY_AMOUNT,
    # 分页
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    # 内容限制
    MIN_ARTICLE_LENGTH,
    MAX_ARTICLE_LENGTH,
    MAX_REVIEW_REVISIONS,
    BOUNTY_CALM_PERIOD_HOURS,
    # 上传限制
    MAX_UPLOAD_FILE_SIZE,
    ALLOWED_IMAGE_TYPES,
    ALLOWED_DOCUMENT_TYPES,
    # 缓存
    CACHE_PREFIX,
    CACHE_TTL,
)

# 导出工具函数
from .utils import (
    # 日期时间
    format_datetime,
    format_datetime_human,
    format_date,
    # 金额
    format_currency,
    parse_currency,
    round_amount,
    # 文本
    truncate_text,
    truncate_html,
    generate_slug,
    mask_string,
    # 随机生成
    generate_random_string,
    generate_numeric_code,
    generate_unique_id,
    # 缓存
    make_cache_key,
    make_cache_key_from_obj,
    # 数值
    clamp,
    calculate_percentage,
    # 安全
    sanitize_filename,
    is_safe_password,
)

__all__ = [
    # 信用等级
    "CreditLevel",
    "CreditLevelConfig",
    # 常量
    "MIN_SKILL_PRICE",
    "MAX_SKILL_PRICE",
    "MIN_BOUNTY_AMOUNT",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "MIN_ARTICLE_LENGTH",
    "MAX_ARTICLE_LENGTH",
    "MAX_REVIEW_REVISIONS",
    "BOUNTY_CALM_PERIOD_HOURS",
    "MAX_UPLOAD_FILE_SIZE",
    "ALLOWED_IMAGE_TYPES",
    "ALLOWED_DOCUMENT_TYPES",
    "CACHE_PREFIX",
    "CACHE_TTL",
    # 日期时间
    "format_datetime",
    "format_datetime_human",
    "format_date",
    # 金额
    "format_currency",
    "parse_currency",
    "round_amount",
    # 文本
    "truncate_text",
    "truncate_html",
    "generate_slug",
    "mask_string",
    # 随机生成
    "generate_random_string",
    "generate_numeric_code",
    "generate_unique_id",
    # 缓存
    "make_cache_key",
    "make_cache_key_from_obj",
    # 数值
    "clamp",
    "calculate_percentage",
    # 安全
    "sanitize_filename",
    "is_safe_password",
]
