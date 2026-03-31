from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class AccessLogMiddleware(MiddlewareMixin):
    """访问日志中间件 - 记录所有访问请求"""
    
    def process_request(self, request):
        # 仅记录路径，不记录参数（避免敏感信息泄露）
        path = request.path
        if request.user.is_authenticated:
            logger.info(f"User {request.user.username} accessed {path}")
        return None

    def process_response(self, request, response):
        return response
