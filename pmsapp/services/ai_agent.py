"""
AI智能体服务 - 处理各种AI任务
包含对话、风险分析、报告生成、任务推荐等功能
"""

import json
import logging
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from django.db.models import Sum, Count

logger = logging.getLogger(__name__)


class ChatResponse:
    """对话响应对象"""
    def __init__(self, content: str, session_id: str = None, metadata: Dict = None):
        self.content = content
        self.session_id = session_id or str(uuid.uuid4())
        self.metadata = metadata or {}
        self.created_at = datetime.now()


class RiskReport:
    """风险报告对象"""
    def __init__(self, project_id: str, risk_level: str, risks: List[Dict], suggestions: List[str]):
        self.project_id = project_id
        self.risk_level = risk_level
        self.risks = risks
        self.suggestions = suggestions
        self.created_at = datetime.now()


class AIAgent:
    """AI智能体，处理各种AI任务"""
    
    def __init__(self):
        self.gateway = None
        self._init_gateway()
    
    def _init_gateway(self):
        """初始化AI网关"""
        try:
            from pmsapp.services.ai_gateway import AIGateway
            self.gateway = AIGateway()
        except Exception as e:
            logger.error(f"初始化AI网关失败: {e}")
    
    def chat(self, user_id: str, message: str, session_id: str = None) -> ChatResponse:
        """
        处理用户对话请求
        
        Args:
            user_id: 用户ID
            message: 用户消息
            session_id: 会话ID，用于维护对话历史
            
        Returns:
            ChatResponse对象，包含响应内容和元数据
        """
        if not self.gateway:
            return ChatResponse("AI服务未配置，请先在设置中配置AI服务")
        
        session_id = session_id or str(uuid.uuid4())
        
        messages = self._build_messages(user_id, message, session_id)
        
        provider = self._get_provider()
        if not provider:
            return ChatResponse("未找到可用的AI配置，请先配置AI服务")
        
        try:
            config = self.gateway.get_config(provider)
            if not config:
                return ChatResponse("AI服务配置无效，请重新配置")
            
            self.gateway.save_config(
                provider=provider,
                api_url=config['api_url'],
                api_key=config['api_key'],
                model_name=config['model_name']
            )
            
            response_text = self.gateway.chat(provider, messages, stream=False)
            
            self._save_chat_history(user_id, session_id, 'user', message)
            self._save_chat_history(user_id, session_id, 'assistant', response_text)
            
            return ChatResponse(response_text, session_id)
        except Exception as e:
            logger.error(f"AI对话失败: {e}")
            return ChatResponse(f"抱歉，AI服务暂时不可用: {str(e)}")
    
    def stream_chat(self, user_id: str, message: str, session_id: str = None):
        """
        流式处理用户对话请求
        
        Args:
            user_id: 用户ID
            message: 用户消息
            session_id: 会话ID
            
        Yields:
            流式响应文本
        """
        if not self.gateway:
            yield "AI服务未配置，请先在设置中配置AI服务"
            return
        
        session_id = session_id or str(uuid.uuid4())
        messages = self._build_messages(user_id, message, session_id)
        
        provider = self._get_provider()
        if not provider:
            yield "未找到可用的AI配置，请先配置AI服务"
            return
        
        try:
            config = self.gateway.get_config(provider)
            if not config:
                yield "AI服务配置无效，请重新配置"
                return
            
            self.gateway.save_config(
                provider=provider,
                api_url=config['api_url'],
                api_key=config['api_key'],
                model_name=config['model_name']
            )
            
            full_response = []
            for chunk in self.gateway.chat(provider, messages, stream=True):
                if chunk:
                    full_response.append(chunk)
                    yield chunk
            
            if full_response:
                self._save_chat_history(user_id, session_id, 'user', message)
                self._save_chat_history(user_id, session_id, 'assistant', ''.join(full_response))
        except Exception as e:
            logger.error(f"AI流式对话失败: {e}")
            yield f"抱歉，AI服务暂时不可用: {str(e)}"
    
    def _build_messages(self, user_id: str, message: str, session_id: str) -> List[Dict]:
        """构建消息列表，包含上下文"""
        messages = [
            {
                'role': 'system',
                'content': '''你是一个专业的项目管理助手，帮助用户进行项目管理和任务规划。
请用简洁专业的语言回复。如果涉及具体数据，请基于用户提供的信息进行分析。'''
            }
        ]
        
        history = self._get_chat_history(user_id, session_id)
        messages.extend(history)
        
        messages.append({'role': 'user', 'content': message})
        
        return messages
    
    def _get_provider(self) -> Optional[str]:
        """获取默认AI提供商"""
        try:
            from pmsapp.models import SystemSettings
            config = SystemSettings.objects.filter(setting_type='ai', is_enabled=True).first()
            if config:
                return config.setting_key
            return None
        except Exception:
            return None
    
    def _get_chat_history(self, user_id: str, session_id: str, limit: int = 20) -> List[Dict]:
        """获取对话历史"""
        try:
            from pmsapp.models import AIChatHistory
            history = AIChatHistory.objects.filter(
                user__user_id=user_id,
                session_id=session_id
            ).order_by('-created_at')[:limit]
            
            return [
                {'role': h.role, 'content': h.content}
                for h in reversed(list(history))
            ]
        except Exception as e:
            logger.warning(f"获取对话历史失败: {e}")
            return []
    
    def _save_chat_history(self, user_id: str, session_id: str, role: str, content: str):
        """保存对话历史"""
        try:
            from pmsapp.models import AIChatHistory, UserInfo
            import uuid
            
            user = UserInfo.objects.filter(user_id=user_id).first()
            if not user:
                return
            
            history_id = f"CHAT-{uuid.uuid4().hex[:12].upper()}"
            
            AIChatHistory.objects.create(
                history_id=history_id,
                user=user,
                session_id=session_id,
                role=role,
                content=content
            )
        except Exception as e:
            logger.warning(f"保存对话历史失败: {e}")
    
    def analyze_risk(self, project_id: str) -> RiskReport:
        """
        分析项目风险
        
        Args:
            project_id: 项目ID
            
        Returns:
            RiskReport对象，包含风险等级、原因和建议
        """
        try:
            from pmsapp.models import ProjectInfo, TaskInfo, BudgetCost
            
            project = ProjectInfo.objects.filter(project_id=project_id).first()
            if not project:
                return RiskReport(project_id, 'unknown', [], ['项目不存在'])
            
            risks = []
            suggestions = []
            risk_level = 'low'
            
            overdue_tasks = TaskInfo.objects.filter(
                project=project,
                plan_end_date__lt=date.today(),
                task_status__in=['进行中', '未开始']
            )
            
            if overdue_tasks.exists():
                overdue_count = overdue_tasks.count()
                risks.append({
                    'type': 'overdue',
                    'count': overdue_count,
                    'description': f'有{overdue_count}个任务已逾期'
                })
                suggestions.append(f'立即处理{overdue_count}个逾期任务，优先处理高优先级任务')
                risk_level = 'high'
            
            budget = getattr(project, 'budget', None)
            if budget:
                if budget.total_budget > 0:
                    cost_ratio = (budget.total_cost / budget.total_budget) * 100
                    if cost_ratio >= 100:
                        risks.append({
                            'type': 'budget',
                            'ratio': cost_ratio,
                            'description': f'预算已超支{ cost_ratio - 100:.1f}%'
                        })
                        suggestions.append('立即审查支出项目，暂停非必要支出')
                        risk_level = 'high'
                    elif cost_ratio >= 80:
                        risks.append({
                            'type': 'budget',
                            'ratio': cost_ratio,
                            'description': f'预算消耗已达{cost_ratio:.1f}%'
                        })
                        suggestions.append('关注预算消耗趋势，控制非必要支出')
                        if risk_level != 'high':
                            risk_level = 'medium'
            
            if project.completion_progress < 50 and project.project_status == '进行中':
                days_elapsed = (date.today() - project.start_date).days if project.start_date else 0
                days_total = project.project_cycle or 1
                expected_progress = (days_elapsed / days_total) * 100
                
                if expected_progress - project.completion_progress > 15:
                    risks.append({
                        'type': 'schedule',
                        'gap': expected_progress - project.completion_progress,
                        'description': f'进度落后计划{expected_progress - project.completion_progress:.1f}%'
                    })
                    suggestions.append('分析进度延迟原因，增加资源投入或调整计划')
                    if risk_level == 'low':
                        risk_level = 'medium'
            
            return RiskReport(project_id, risk_level, risks, suggestions)
        except Exception as e:
            logger.error(f"风险分析失败: {e}")
            return RiskReport(project_id, 'error', [], [f'分析失败: {str(e)}'])
    
    def generate_report(self, user_id: str, report_type: str = 'weekly') -> str:
        """
        生成工作报告
        
        Args:
            user_id: 用户ID
            report_type: 报告类型 ('weekly' 或 'monthly')
            
        Returns:
            生成的报告内容
        """
        try:
            from pmsapp.models import UserInfo, TaskInfo, WeeklySummary
            
            user = UserInfo.objects.filter(user_id=user_id).first()
            if not user:
                return "用户不存在"
            
            today = date.today()
            
            if report_type == 'weekly':
                week_start = today - datetime.timedelta(days=today.weekday())
                week_end = week_start + datetime.timedelta(days=6)
                period_str = f"{week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}"
                
                tasks = TaskInfo.objects.filter(
                    task_owner=user,
                    plan_start_date__lte=week_end,
                    plan_end_date__gte=week_start
                )
            else:
                month_start = today.replace(day=1)
                if today.month == 12:
                    month_end = today.replace(year=today.year + 1, month=1, day=1) - datetime.timedelta(days=1)
                else:
                    month_end = today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1)
                period_str = f"{month_start.strftime('%Y-%m-%d')} 至 {month_end.strftime('%Y-%m-%d')}"
                
                tasks = TaskInfo.objects.filter(
                    task_owner=user,
                    plan_start_date__lte=month_end,
                    plan_end_date__gte=month_start
                )
            
            completed = tasks.filter(task_status='已完成').count()
            in_progress = tasks.filter(task_status='进行中').count()
            not_started = tasks.filter(task_status='未开始').count()
            total = tasks.count()
            
            completion_rate = (completed / total * 100) if total > 0 else 0
            
            context_prompt = f'''请根据以下信息生成{report_type == 'weekly' and '周' or '月'}工作报告：

统计周期：{period_str}
用户：{user.user_name}
任务完成情况：
- 总任务数：{total}
- 已完成：{completed}
- 进行中：{in_progress}
- 未开始：{not_started}
- 完成率：{completion_rate:.1f}%

请生成一份专业的工作报告，包含：
1. 工作总结
2. 任务完成情况分析
3. 存在的问题
4. 下期工作计划

请用中文回复。'''
            
            provider = self._get_provider()
            if not provider or not self.gateway:
                return self._generate_simple_report(user, tasks, completed, in_progress, not_started, report_type, period_str)
            
            config = self.gateway.get_config(provider)
            if not config:
                return self._generate_simple_report(user, tasks, completed, in_progress, not_started, report_type, period_str)
            
            self.gateway.save_config(
                provider=provider,
                api_url=config['api_url'],
                api_key=config['api_key'],
                model_name=config['model_name']
            )
            
            messages = [
                {'role': 'system', 'content': '你是一个专业的项目管理助手，擅长生成简洁清晰的工作报告。'},
                {'role': 'user', 'content': context_prompt}
            ]
            
            report = self.gateway.chat(provider, messages, stream=False)
            return report
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return f"报告生成失败: {str(e)}"
    
    def _generate_simple_report(self, user, tasks, completed, in_progress, not_started, report_type, period_str):
        """生成简单文本报告（当AI不可用时）"""
        total = completed + in_progress + not_started
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        report = f'''
{report_type == 'weekly' and '周' or '月'}工作报告
==================
统计周期：{period_str}
用户：{user.user_name}

一、任务完成情况
- 总任务数：{total}
- 已完成：{completed}
- 进行中：{in_progress}
- 未开始：{not_started}
- 完成率：{completion_rate:.1f}%

二、工作总结
'''
        if completed > 0:
            report += f'本周期共完成{completed}项任务，'
            if completion_rate >= 80:
                report += '任务完成情况良好。'
            elif completion_rate >= 50:
                report += '任务完成情况一般，需要加快进度。'
            else:
                report += '任务完成率较低，需要加强执行力。'
        else:
            report += '本周期暂无完成的任务。'
        
        report += '\n\n三、下期工作计划\n'
        if in_progress > 0:
            report += f'继续推进{in_progress}个进行中的任务，'
            if not_started > 0:
                report += f'启动{not_started}个未开始的任务。'
            else:
                report += '确保按时完成。'
        elif not_started > 0:
            report += f'启动{not_started}个计划中的任务，合理安排时间。'
        else:
            report += '暂无明确的工作计划。'
        
        return report
    
    def recommend_assignee(self, task_data: dict) -> List[dict]:
        """
        智能推荐任务负责人
        
        Args:
            task_data: 任务数据，包含 project_id, task_type, expected_hours 等
            
        Returns:
            推荐负责人列表，按适合度排序
        """
        try:
            from pmsapp.models import UserInfo, TaskInfo
            
            project_id = task_data.get('project_id')
            if not project_id:
                return []
            
            users = UserInfo.objects.all()
            recommendations = []
            
            for user in users:
                current_tasks = TaskInfo.objects.filter(
                    task_owner=user,
                    task_status__in=['进行中', '未开始']
                ).count()
                
                workload_score = max(0, 100 - current_tasks * 20)
                
                team_match = 0
                if hasattr(user, 'team_name') and user.team_name:
                    team_match = 50
                
                skill_match = 50
                
                total_score = workload_score * 0.4 + team_match * 0.3 + skill_match * 0.3
                
                recommendations.append({
                    'user_id': user.user_id,
                    'user_name': user.user_name,
                    'score': total_score,
                    'current_tasks': current_tasks,
                    'reason': self._generate_recommend_reason(workload_score, team_match, skill_match)
                })
            
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            
            return recommendations[:5]
        except Exception as e:
            logger.error(f"任务推荐失败: {e}")
            return []
    
    def _generate_recommend_reason(self, workload: float, team: float, skill: float) -> str:
        """生成推荐理由"""
        reasons = []
        if workload >= 60:
            reasons.append('当前工作负载较轻')
        elif workload < 30:
            reasons.append('工作负载较重')
        
        if team >= 40:
            reasons.append('团队匹配度高')
        
        if skill >= 40:
            reasons.append('技能匹配')
        
        return '，'.join(reasons) if reasons else '综合评估'
    
    def get_chat_sessions(self, user_id: str, limit: int = 10) -> List[Dict]:
        """获取用户的会话列表"""
        try:
            from pmsapp.models import AIChatHistory
            sessions = AIChatHistory.objects.filter(
                user__user_id=user_id
            ).values('session_id').annotate(
                last_message=models.Max('created_at'),
                message_count=Count('id')
            ).order_by('-last_message')[:limit]
            
            return [
                {
                    'session_id': s['session_id'],
                    'last_message': s['last_message'].strftime('%Y-%m-%d %H:%M') if s['last_message'] else '',
                    'message_count': s['message_count']
                }
                for s in sessions
            ]
        except Exception as e:
            logger.warning(f"获取会话列表失败: {e}")
            return []
    
    def clear_chat_history(self, user_id: str, session_id: str = None):
        """清除对话历史"""
        try:
            from pmsapp.models import AIChatHistory
            
            query = AIChatHistory.objects.filter(user__user_id=user_id)
            if session_id:
                query = query.filter(session_id=session_id)
            
            query.delete()
            return True
        except Exception as e:
            logger.error(f"清除对话历史失败: {e}")
            return False
