"""
AI API路由 - 处理AI相关的REST API请求
所有API都需要登录认证
"""

import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def ai_chat(request):
    """AI对话接口"""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not message:
            return JsonResponse({'success': False, 'error': '消息不能为空'})
        
        user_id = _get_user_id(request)
        if not user_id:
            return JsonResponse({'success': False, 'error': '用户未认证'})
        
        from pmsapp.services.ai_agent import AIAgent
        agent = AIAgent()
        
        response = agent.chat(user_id, message, session_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'content': response.content,
                'session_id': response.session_id,
                'created_at': response.created_at.isoformat()
            }
        })
    except Exception as e:
        logger.error("AI对话失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def ai_chat_history(request):
    """获取AI对话历史"""
    try:
        session_id = request.GET.get('session_id')
        
        user_id = _get_user_id(request)
        if not user_id:
            return JsonResponse({'success': False, 'error': '用户未认证'})
        
        from pmsapp.services.ai_agent import AIAgent
        agent = AIAgent()
        
        if session_id:
            history = agent._get_chat_history(user_id, session_id)
            return JsonResponse({'success': True, 'data': history})
        else:
            sessions = agent.get_chat_sessions(user_id)
            return JsonResponse({'success': True, 'data': sessions})
    except Exception as e:
        logger.error("获取对话历史失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["DELETE"])
def ai_chat_clear(request):
    """清除AI对话历史"""
    try:
        session_id = request.GET.get('session_id')
        
        user_id = _get_user_id(request)
        if not user_id:
            return JsonResponse({'success': False, 'error': '用户未认证'})
        
        from pmsapp.services.ai_agent import AIAgent
        agent = AIAgent()
        
        success = agent.clear_chat_history(user_id, session_id)
        
        return JsonResponse({'success': success})
    except Exception as e:
        logger.error("清除对话历史失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST", "GET"])
def ai_config(request):
    """AI配置接口"""
    try:
        user_id = _get_user_id(request)
        if not user_id:
            return JsonResponse({'success': False, 'error': '用户未认证'})
        
        from pmsapp.services.ai_gateway import AIGateway
        gateway = AIGateway()
        
        if request.method == "GET":
            provider = request.GET.get('provider')
            config = gateway.get_config(provider)
            
            if config:
                config['api_key'] = '********' if config.get('api_key') else ''
            
            return JsonResponse({'success': True, 'data': config})
        
        else:
            data = json.loads(request.body)
            provider = data.get('provider', 'openai')
            api_url = data.get('api_url', '')
            api_key = data.get('api_key', '')
            model_name = data.get('model_name', '')
            is_default = data.get('is_default', True)
            
            if not api_url or not api_key or not model_name:
                return JsonResponse({'success': False, 'error': '缺少必要参数'})
            
            success = gateway.save_config(provider, api_url, api_key, model_name, is_default)
            
            return JsonResponse({'success': success})
    except Exception as e:
        logger.error("AI配置失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def ai_config_validate(request):
    """验证AI配置"""
    try:
        data = json.loads(request.body)
        
        from pmsapp.services.ai_gateway import AIGateway
        gateway = AIGateway()
        
        is_valid, message = gateway.validate_config(data)
        
        return JsonResponse({
            'success': True,
            'data': {
                'valid': is_valid,
                'message': message
            }
        })
    except Exception as e:
        logger.error("AI配置验证失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def ai_analyze_risk(request):
    """分析项目风险"""
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        
        if not project_id:
            return JsonResponse({'success': False, 'error': '项目ID不能为空'})
        
        from pmsapp.services.ai_agent import AIAgent
        agent = AIAgent()
        
        report = agent.analyze_risk(project_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'project_id': report.project_id,
                'risk_level': report.risk_level,
                'risks': report.risks,
                'suggestions': report.suggestions,
                'created_at': report.created_at.isoformat()
            }
        })
    except Exception as e:
        logger.error("风险分析失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def ai_generate_report(request):
    """生成分析报告"""
    try:
        data = json.loads(request.body)
        report_type = data.get('report_type', 'weekly')
        
        user_id = _get_user_id(request)
        if not user_id:
            return JsonResponse({'success': False, 'error': '用户未认证'})
        
        from pmsapp.services.ai_agent import AIAgent
        agent = AIAgent()
        
        report = agent.generate_report(user_id, report_type)
        
        return JsonResponse({
            'success': True,
            'data': {
                'report_type': report_type,
                'content': report
            }
        })
    except Exception as e:
        logger.error("生成报告失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def ai_recommend_task(request):
    """推荐任务分配"""
    try:
        data = json.loads(request.body)
        task_data = {
            'project_id': data.get('project_id'),
            'task_type': data.get('task_type'),
            'expected_hours': data.get('expected_hours')
        }
        
        from pmsapp.services.ai_agent import AIAgent
        agent = AIAgent()
        
        recommendations = agent.recommend_assignee(task_data)
        
        return JsonResponse({
            'success': True,
            'data': recommendations
        })
    except Exception as e:
        logger.error("任务推荐失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def workflow_rules(request, rule_id=None):
    """工作流规则管理接口"""
    try:
        user_id = _get_user_id(request)
        if not user_id:
            return JsonResponse({'success': False, 'error': '用户未认证'})
        
        from pmsapp.services.workflow_engine import WorkflowEngine, WorkflowRule
        engine = WorkflowEngine()
        
        if request.method == "GET":
            trigger_type = request.GET.get('trigger_type')
            rules = engine.get_rules(trigger_type)
            return JsonResponse({
                'success': True,
                'data': [r.to_dict() for r in rules]
            })
        
        elif request.method == "POST":
            data = json.loads(request.body)
            rule = WorkflowRule(
                rule_id='',
                rule_name=data.get('rule_name', ''),
                trigger_type=data.get('trigger_type', 'manual'),
                trigger_condition=data.get('trigger_condition', {}),
                action_type=data.get('action_type', 'send_notification'),
                action_config=data.get('action_config', {}),
                is_enabled=data.get('is_enabled', True),
                created_by=user_id
            )
            success = engine.add_rule(rule)
            return JsonResponse({'success': success})
        
        elif request.method == "PUT" and rule_id:
            data = json.loads(request.body)
            rule = WorkflowRule(
                rule_id=rule_id,
                rule_name=data.get('rule_name', ''),
                trigger_type=data.get('trigger_type', 'manual'),
                trigger_condition=data.get('trigger_condition', {}),
                action_type=data.get('action_type', 'send_notification'),
                action_config=data.get('action_config', {}),
                is_enabled=data.get('is_enabled', True)
            )
            success = engine.update_rule(rule)
            return JsonResponse({'success': success})
        
        elif request.method == "DELETE" and rule_id:
            success = engine.delete_rule(rule_id)
            return JsonResponse({'success': success})
        
        return JsonResponse({'success': False, 'error': '无效的请求'})
    except Exception as e:
        logger.error("工作流规则管理失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def workflow_logs(request):
    """获取工作流执行日志"""
    try:
        rule_id = request.GET.get('rule_id')
        limit = int(request.GET.get('limit', 50))
        
        from pmsapp.services.workflow_engine import WorkflowEngine
        engine = WorkflowEngine()
        
        logs = engine.get_execution_log(rule_id, limit)
        
        return JsonResponse({
            'success': True,
            'data': logs
        })
    except Exception as e:
        logger.error("获取工作流日志失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def risk_alerts(request):
    """获取风险预警列表"""
    try:
        project_id = request.GET.get('project_id')
        resolved = request.GET.get('resolved', 'false').lower() == 'true'
        
        from pmsapp.models import RiskAlert
        
        query = RiskAlert.objects.filter(is_resolved=resolved)
        if project_id:
            query = query.filter(project__project_id=project_id)
        
        alerts = query.order_by('-created_at')[:50]
        
        return JsonResponse({
            'success': True,
            'data': [
                {
                    'alert_id': a.alert_id,
                    'project_id': a.project.project_id,
                    'project_name': a.project.project_name,
                    'alert_type': a.alert_type,
                    'risk_level': a.risk_level,
                    'description': a.description,
                    'suggestion': a.suggestion,
                    'is_resolved': a.is_resolved,
                    'created_at': a.created_at.isoformat() if a.created_at else None
                }
                for a in alerts
            ]
        })
    except Exception as e:
        logger.error("获取风险预警失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def risk_alert_resolve(request, alert_id):
    """标记风险预警为已解决"""
    try:
        from pmsapp.services.analyzer import RiskAnalyzer
        analyzer = RiskAnalyzer()
        
        success = analyzer.resolve_alert(alert_id)
        
        return JsonResponse({'success': success})
    except Exception as e:
        logger.error("解决风险预警失败")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def risk_check(request):
    """手动触发风险检测"""
    try:
        data = json.loads(request.body)
        check_types = data.get('types', ['overdue', 'budget', 'schedule'])
        
        from pmsapp.services.analyzer import RiskAnalyzer
        analyzer = RiskAnalyzer()
        
        results = {}
        
        if 'overdue' in check_types:
            results['overdue'] = [a.to_dict() for a in analyzer.check_overdue_tasks()]
        
        if 'budget' in check_types:
            results['budget'] = [a.to_dict() for a in analyzer.check_budget_risk()]
        
        if 'schedule' in check_types:
            results['schedule'] = [a.to_dict() for a in analyzer.check_schedule_risk()]
        
        return JsonResponse({
            'success': True,
            'data': results
        })
    except Exception as e:
        logger.error("风险检测失败")
        return JsonResponse({'success': False, 'error': str(e)})


def _get_user_id(request):
    """获取当前用户ID"""
    try:
        if hasattr(request, 'user') and request.user.is_authenticated:
            return request.user.username
        return None
    except Exception:
        return None
