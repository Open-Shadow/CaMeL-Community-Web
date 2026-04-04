from ninja import NinjaAPI
from apps.accounts.api import router as accounts_router
from apps.skills.api import router as skills_router
from apps.bounties.api import router as bounties_router
from apps.workshop.api import router as workshop_router
from apps.payments.api import router as payments_router
from apps.notifications.api import router as notifications_router
from apps.search.api import router as search_router

api = NinjaAPI(title="CaMeL Community API", version="1.0.0")

api.add_router("/accounts/", accounts_router)
api.add_router("/skills/", skills_router)
api.add_router("/bounties/", bounties_router)
api.add_router("/workshop/", workshop_router)
api.add_router("/payments/", payments_router)
api.add_router("/notifications/", notifications_router)
api.add_router("/search/", search_router)
