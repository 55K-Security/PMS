from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class AccessLogMiddleware(MiddlewareMixin):
    """访问日志中间件 - 记录所有访问请求"""
    
    def process_request(self, request):
        # 记录访问日志
        if request.user.is_authenticated:
            logger.info(f"User {request.user.username} accessed {request.path}")
        return None
    
    def process_response(self, request, response):
        return response
