class TimezoneMiddleware(object):

    def process_request(self, request):
        if hasattr(request.user, 'activate_timezone'):
            request.user.activate_timezone()