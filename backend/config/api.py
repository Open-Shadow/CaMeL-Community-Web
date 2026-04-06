from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError

from apps.accounts.api import router as accounts_router
from apps.accounts.user_api import router as user_router
from apps.accounts.invitation_api import router as invitation_router
from apps.skills.api import router as skills_router
from apps.bounties.api import router as bounties_router
from apps.workshop.api import router as workshop_router
from apps.payments.api import router as payments_router
from apps.notifications.api import router as notifications_router
from apps.credits.api import router as credits_router
from apps.search.api import router as search_router
from apps.accounts.admin_api import router as admin_router
from apps.credits.ranking_api import router as rankings_router

api = NinjaAPI(title="CaMeL Community API", version="1.0.0")


@api.exception_handler(AuthenticationError)
def authentication_error_handler(request, exc):
    return JsonResponse({"detail": "Unauthorized"}, status=401)

api.add_router("/auth/", accounts_router)
api.add_router("/users/", user_router)
api.add_router("/invitations/", invitation_router)
api.add_router("/skills/", skills_router)
api.add_router("/bounties/", bounties_router)
api.add_router("/workshop/", workshop_router)
api.add_router("/payments/", payments_router)
api.add_router("/notifications/", notifications_router)
api.add_router("/credits/", credits_router)
api.add_router("/search/", search_router)
api.add_router("/admin/", admin_router)
api.add_router("/rankings/", rankings_router)
