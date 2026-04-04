from django.db import models
from apps.accounts.models import User


class CreditAction(models.TextChoices):
    REGISTER = "REGISTER", "注册奖励"
    PUBLISH_SKILL = "PUBLISH_SKILL", "发布 Skill"
    SKILL_CALLED = "SKILL_CALLED", "Skill 被调用"
    PUBLISH_ARTICLE = "PUBLISH_ARTICLE", "发布文章"
    ARTICLE_FEATURED = "ARTICLE_FEATURED", "文章加精"
    BOUNTY_COMPLETED = "BOUNTY_COMPLETED", "完成悬赏"
    TIP_GIVEN = "TIP_GIVEN", "打赏他人"
    ARBITRATION_SERVED = "ARBITRATION_SERVED", "参与仲裁"
    INVITE_REGISTERED = "INVITE_REGISTERED", "邀请注册"
    BOUNTY_TIMEOUT = "BOUNTY_TIMEOUT", "悬赏超时惩罚"
    BOUNTY_FREEZE = "BOUNTY_FREEZE", "悬赏板冻结"
    ADMIN_ADJUST = "ADMIN_ADJUST", "管理员调整"


class CreditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="credit_logs")
    action = models.CharField(max_length=30, choices=CreditAction.choices)
    amount = models.IntegerField()
    score_before = models.IntegerField()
    score_after = models.IntegerField()
    reference_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "credits_credit_log"
        indexes = [models.Index(fields=["user", "created_at"])]
