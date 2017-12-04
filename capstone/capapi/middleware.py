import logging
import time

logger = logging.getLogger(__name__)


class RequestLogMiddleware(object):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        data = {
            'request': {
                'method': request.method,
                'path':  request.path,
                'query': getattr(request, request.method).dict(),
            },
            'response': {
                'status': response.status_code
            },
            'time': time.time() - request.start_time,
        }

        logger.info(data)
        return response


