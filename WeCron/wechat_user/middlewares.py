from django.utils.deprecation import MiddlewareMixin


class TimezoneMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if hasattr(request.user, 'activate_timezone'):
            request.user.activate_timezone()
