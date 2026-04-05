"""Invitation API routes."""
from ninja import Router, Schema

from common.permissions import AuthBearer
from apps.accounts.services import InvitationService


router = Router(tags=["invitations"], auth=AuthBearer())


# =============================================================================
# Schemas
# =============================================================================

class InviteCodeOutput(Schema):
    code: str


class InviteStatsOutput(Schema):
    total_codes: int
    used_codes: int
    remaining_this_month: int


class InvitationOutput(Schema):
    id: int
    code: str
    used_by_name: str
    used_at: str
    created_at: str


class ValidateCodeInput(Schema):
    code: str


class MessageOutput(Schema):
    message: str


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/generate", response={200: InviteCodeOutput, 400: MessageOutput})
def generate_invite_code(request):
    """Generate a new invitation code."""
    try:
        code = InvitationService.generate_code(request.auth)
        return 200, {"code": code}
    except ValueError as e:
        return 400, {"message": str(e)}


@router.get("/stats", response=InviteStatsOutput)
def get_invite_stats(request):
    """Get invitation statistics."""
    return InvitationService.get_stats(request.auth)


@router.get("/list", response=list[InvitationOutput])
def list_invitations(request):
    """List all invitations by current user."""
    invitations = InvitationService.get_my_invitations(request.auth)
    return [
        {
            "id": inv.id,
            "code": inv.code,
            "used_by_name": (
                inv.used_by.display_name or inv.used_by.email
                if inv.used_by else ""
            ),
            "used_at": inv.used_at.isoformat() if inv.used_at else "",
            "created_at": inv.created_at.isoformat(),
        }
        for inv in invitations.select_related("used_by")
    ]


@router.post("/validate", response={200: MessageOutput, 400: MessageOutput},
             auth=None)
def validate_invite_code(request, data: ValidateCodeInput):
    """Validate an invitation code (public endpoint)."""
    _, error = InvitationService.validate_code(data.code)
    if error:
        return 400, {"message": error}
    return 200, {"message": "邀请码有效"}
