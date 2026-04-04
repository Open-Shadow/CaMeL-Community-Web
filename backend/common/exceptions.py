from ninja import NinjaAPI
from ninja.errors import ValidationError, AuthenticationError
from django.http import HttpRequest


def add_exception_handlers(api: NinjaAPI):
    @api.exception_handler(ValidationError)
    def validation_error(request: HttpRequest, exc: ValidationError):
        return api.create_response(request, {"detail": exc.errors}, status=422)

    @api.exception_handler(AuthenticationError)
    def auth_error(request: HttpRequest, exc: AuthenticationError):
        return api.create_response(request, {"detail": "Unauthorized"}, status=401)

    @api.exception_handler(Exception)
    def generic_error(request: HttpRequest, exc: Exception):
        return api.create_response(request, {"detail": str(exc)}, status=500)
