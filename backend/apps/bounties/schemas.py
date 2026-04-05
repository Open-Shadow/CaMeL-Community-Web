"""Bounties Pydantic schemas."""
from ninja import Schema


class BountyCreateInput(Schema):
    title: str
    description: str
    bounty_type: str
    reward: float
    deadline: str


class BountyApplicationInput(Schema):
    proposal: str
    estimated_days: int


class BountyDeliverableInput(Schema):
    content: str
    attachments: list[str] = []


class BountyDecisionInput(Schema):
    feedback: str = ""


class BountyCommentInput(Schema):
    content: str


class ArbitrationStatementInput(Schema):
    content: str


class ArbitrationVoteInput(Schema):
    vote: str
    hunter_ratio: float | None = None


class ArbitrationAppealInput(Schema):
    reason: str = ""


class AdminArbitrationDecisionInput(Schema):
    result: str
    hunter_ratio: float | None = None


class BountyReviewInput(Schema):
    quality_rating: int
    communication_rating: int
    responsiveness_rating: int
    comment: str = ""


class BountyUserOut(Schema):
    id: int
    username: str
    display_name: str
    level: str
    credit_score: int


class BountyApplicationOut(Schema):
    id: int
    proposal: str
    estimated_days: int
    applicant: BountyUserOut
    created_at: str


class BountyDeliverableOut(Schema):
    id: int
    content: str
    attachments: list[str]
    revision_number: int
    submitter: BountyUserOut
    created_at: str


class BountyCommentOut(Schema):
    id: int
    content: str
    author: BountyUserOut
    created_at: str


class ArbitrationVoteOut(Schema):
    id: int
    arbitrator: BountyUserOut
    vote: str
    hunter_ratio: float | None = None
    created_at: str


class ArbitrationOut(Schema):
    id: int
    creator_statement: str
    hunter_statement: str
    result: str
    hunter_ratio: float | None = None
    appeal_by_id: int | None = None
    appeal_fee_paid: bool
    admin_final_result: str
    deadline: str | None = None
    resolved_at: str | None = None
    arbitrators: list[BountyUserOut]
    votes: list[ArbitrationVoteOut]


class BountyReviewOut(Schema):
    id: int
    reviewer: BountyUserOut
    reviewee: BountyUserOut
    quality_rating: int
    communication_rating: int
    responsiveness_rating: int
    comment: str
    created_at: str


class BountySummaryOut(Schema):
    id: int
    title: str
    description: str
    bounty_type: str
    reward: float
    status: str
    deadline: str
    revision_count: int
    is_cold: bool
    application_count: int
    creator: BountyUserOut
    accepted_applicant: BountyUserOut | None = None
    created_at: str
    updated_at: str


class BountyDetailOut(BountySummaryOut):
    applications: list[BountyApplicationOut]
    deliverables: list[BountyDeliverableOut]
    comments: list[BountyCommentOut]
    reviews: list[BountyReviewOut]
    arbitration: ArbitrationOut | None = None


class BountyListOut(Schema):
    items: list[BountySummaryOut]
    total: int
    limit: int
    offset: int


class MessageOut(Schema):
    message: str


class ActiveDisputeOut(Schema):
    id: int
    title: str
    status: str
    creator: BountyUserOut
    accepted_applicant: BountyUserOut | None = None
    arbitration: ArbitrationOut | None = None
