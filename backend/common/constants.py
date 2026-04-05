"""
通用常量定义
"""

from enum import Enum


# =============================================================================
# 信用等级体系
# =============================================================================

class CreditLevel:
    """信用等级定义"""

    SPROUT = "sprout"
    CRAFTSMAN = "craftsman"
    EXPERT = "expert"
    MASTER = "master"
    GRANDMASTER = "grandmaster"


class CreditLevelConfig:
    """信用等级配置"""

    # 等级阈值
    SPROUT_MAX = 99
    CRAFTSMAN_MIN = 100
    CRAFTSMAN_MAX = 499
    EXPERT_MIN = 500
    EXPERT_MAX = 1999
    MASTER_MIN = 2000
    MASTER_MAX = 4999
    GRANDMASTER_MIN = 5000

    # 等级信息
    LEVELS = [
        (CreditLevel.GRANDMASTER, "宗师", "👑", GRANDMASTER_MIN, None),
        (CreditLevel.MASTER, "大师", "🏆", MASTER_MIN, MASTER_MAX),
        (CreditLevel.EXPERT, "专家", "⚡", EXPERT_MIN, EXPERT_MAX),
        (CreditLevel.CRAFTSMAN, "工匠", "🔧", CRAFTSMAN_MIN, CRAFTSMAN_MAX),
        (CreditLevel.SPROUT, "新芽", "🌱", 0, SPROUT_MAX),
    ]

    # API 调用折扣率
    DISCOUNTS = {
        CreditLevel.SPROUT: 1.0,
        CreditLevel.CRAFTSMAN: 0.95,
        CreditLevel.EXPERT: 0.90,
        CreditLevel.MASTER: 0.85,
        CreditLevel.GRANDMASTER: 0.80,
    }

    @classmethod
    def get_level_by_score(cls, score: int) -> tuple:
        """
        根据分数获取等级信息

        Returns: (level_key, level_name, icon, min_score, max_score)
        """
        for level in cls.LEVELS:
            min_score, max_score = level[3], level[4]
            if score >= min_score and (max_score is None or score <= max_score):
                return level
        return cls.LEVELS[-1]

    @classmethod
    def get_discount(cls, score: int) -> float:
        """根据分数获取 API 折扣率"""
        level = cls.get_level_by_score(score)
        return cls.DISCOUNTS.get(level[0], 1.0)


# =============================================================================
# Skill 价格范围
# =============================================================================

MIN_SKILL_PRICE = 0.01
MAX_SKILL_PRICE = 10.00

# =============================================================================
# 分页默认值
# =============================================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# =============================================================================
# 内容限制
# =============================================================================

# 悬赏任务
MIN_BOUNTY_AMOUNT = 1.00
BOUNTY_CALM_PERIOD_HOURS = 24  # 仲裁冷静期（小时）
BOUNTY_FREEZE_THRESHOLD = 30  # 信用分低于此值冻结悬赏板

# 信用分门槛
CREDIT_BOUNTY_POST_MIN = 50  # 发布悬赏最低信用分
CREDIT_BOUNTY_APPLY_MIN = 50  # 接单悬赏最低信用分
CREDIT_ARBITRATION_MIN = 500  # 参与仲裁最低信用分

# 文章
MIN_ARTICLE_LENGTH = 500
MAX_ARTICLE_LENGTH = 2000

# 评价
MAX_REVIEW_REVISIONS = 3

# 邀请码
INVITE_CODE_LENGTH = 8

# =============================================================================
# 文件上传限制
# =============================================================================

MAX_UPLOAD_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
ALLOWED_DOCUMENT_TYPES = ["application/pdf", "text/markdown", "text/plain"]

# =============================================================================
# 缓存键前缀
# =============================================================================

CACHE_PREFIX = {
    "hot_skills": "hot:skills",
    "hot_articles": "hot:articles",
    "user_profile": "user:profile",
    "user_credit": "user:credit",
    "skill_detail": "skill:detail",
    "search_results": "search:results",
}

# =============================================================================
# 超时时间（秒）
# =============================================================================

CACHE_TTL = {
    "hot_skills": 300,  # 5分钟
    "hot_articles": 300,
    "user_profile": 3600,  # 1小时
    "skill_detail": 600,  # 10分钟
    "search_results": 60,
}
