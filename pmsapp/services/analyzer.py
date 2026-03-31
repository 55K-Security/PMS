"""
数据分析服务 - 风险预警和报告生成
包含风险分析器、报告生成器等
"""

import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Generator
from decimal import Decimal

logger = logging.getLogger(__name__)


class RiskAlert:
    """风险预警对象"""
    
    RISK_LEVELS = ['low', 'medium', 'high', 'critical']
    
    def __init__(self, alert_id: str, project_id: str, project_name: str,
                 alert_type: str, risk_level: str, description: str,
                 suggestion: str = '', is_resolved: bool = False):
        self.alert_id = alert_id
        self.project_id = project_id
        self.project_name = project_name
        self.alert_type = alert_type
        self.risk_level = risk_level
        self.description = description
        self.suggestion = suggestion
        self.is_resolved = is_resolved
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'alert_id': self.alert_id,
            'project_id': self.project_id,
            'project_name': self.project_name,
            'alert_type': self.alert_type,
            'risk_level': self.risk_level,
            'description': self.description,
            'suggestion': self.suggestion,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class RiskAnalyzer:
    """风险分析器"""
    
    def __init__(self):
        self.alerts: List[RiskAlert] = []
    
    def check_overdue_tasks(self, days_threshold: int = 3) -> List[RiskAlert]:
        """
        检测逾期任务
        
        Args:
            days_threshold: 逾期天数阈值，超过此天数才生成预警
            
        Returns:
            风险预警列表
        """
        alerts = []
        try:
            from pmsapp.models import TaskInfo, ProjectInfo
            
            today = date.today()
            overdue_tasks = TaskInfo.objects.filter(
                plan_end_date__lt=today,
                task_status__in=['进行中', '未开始']
            )
            
            for task in overdue_tasks:
                overdue_days = (today - task.plan_end_date).days
                
                if overdue_days >= days_threshold:
                    if overdue_days >= days_threshold * 2:
                        risk_level = 'high'
                    elif overdue_days >= days_threshold:
                        risk_level = 'medium'
                    else:
                        risk_level = 'low'
                    
                    alert_id = f"ALERT-{today.strftime('%Y%m%d')}-{task.task_id}"
                    
                    alert = RiskAlert(
                        alert_id=alert_id,
                        project_id=task.project.project_id,
                        project_name=task.project.project_name,
                        alert_type='task_overdue',
                        risk_level=risk_level,
                        description=f'任务"{task.key_content_name}"已逾期{overdue_days}天',
                        suggestion=f'优先处理高优先级任务，评估是否需要调整计划或增加资源'
                    )
                    alerts.append(alert)
                    
                    self._save_alert(alert)
            
            return alerts
        except Exception as e:
            logger.error(f"检测逾期任务失败: {e}")
            return []
    
    def check_budget_risk(self, project_id: str = None) -> List[RiskAlert]:
        """
        检测预算风险
        
        Args:
            project_id: 可选，指定项目ID
            
        Returns:
            风险预警列表
        """
        alerts = []
        try:
            from pmsapp.models import BudgetCost, ProjectInfo
            
            query = BudgetCost.objects.all()
            if project_id:
                query = query.filter(project__project_id=project_id)
            
            for budget in query:
                if budget.total_budget <= 0:
                    continue
                
                cost_ratio = (budget.total_cost / budget.total_budget) * 100
                
                if cost_ratio >= 100:
                    risk_level = 'critical'
                elif cost_ratio >= 90:
                    risk_level = 'high'
                elif cost_ratio >= 80:
                    risk_level = 'medium'
                else:
                    continue
                
                alert_id = f"ALERT-{date.today().strftime('%Y%m%d')}-BUDGET-{budget.budget_id}"
                
                over_amount = budget.total_cost - budget.total_budget
                alert = RiskAlert(
                    alert_id=alert_id,
                    project_id=budget.project.project_id,
                    project_name=budget.project_name,
                    alert_type='budget_exceeded',
                    risk_level=risk_level,
                    description=f'项目预算{"已超支" if over_amount >= 0 else "消耗接近上限"}，消耗比例{cost_ratio:.1f}%',
                    suggestion='立即审查支出项目，暂停非必要支出，考虑申请追加预算' if risk_level in ['high', 'critical'] else '关注预算消耗趋势'
                )
                alerts.append(alert)
                
                self._save_alert(alert)
            
            return alerts
        except Exception as e:
            logger.error(f"检测预算风险失败: {e}")
            return []
    
    def check_schedule_risk(self, project_id: str = None) -> List[RiskAlert]:
        """
        检测进度风险
        
        Args:
            project_id: 可选，指定项目ID
            
        Returns:
            风险预警列表
        """
        alerts = []
        try:
            from pmsapp.models import ProjectInfo
            
            query = ProjectInfo.objects.filter(project_status='进行中')
            if project_id:
                query = query.filter(project_id=project_id)
            
            today = date.today()
            
            for project in query:
                if not project.start_date or not project.end_date:
                    continue
                
                total_days = project.project_cycle
                if total_days <= 0:
                    continue
                
                days_elapsed = (today - project.start_date).days
                if days_elapsed < 0:
                    continue
                
                expected_progress = min(100, (days_elapsed / total_days) * 100)
                actual_progress = float(project.completion_progress or 0)
                
                delay_percent = expected_progress - actual_progress
                
                if delay_percent >= 20:
                    risk_level = 'high'
                elif delay_percent >= 10:
                    risk_level = 'medium'
                elif delay_percent >= 5:
                    risk_level = 'low'
                else:
                    continue
                
                alert_id = f"ALERT-{today.strftime('%Y%m%d')}-SCHEDULE-{project.project_id}"
                
                alert = RiskAlert(
                    alert_id=alert_id,
                    project_id=project.project_id,
                    project_name=project.project_name,
                    alert_type='schedule_delayed',
                    risk_level=risk_level,
                    description=f'项目进度落后计划{delay_percent:.1f}%，预期进度{expected_progress:.1f}%，实际进度{actual_progress:.1f}%',
                    suggestion='分析进度延迟原因，增加资源投入或调整计划'
                )
                alerts.append(alert)
                
                self._save_alert(alert)
            
            return alerts
        except Exception as e:
            logger.error(f"检测进度风险失败: {e}")
            return []
    
    def check_all_risks(self) -> Dict[str, List[RiskAlert]]:
        """
        执行全面风险检测
        
        Returns:
            各类风险预警字典
        """
        results = {
            'overdue_tasks': self.check_overdue_tasks(),
            'budget_risks': self.check_budget_risk(),
            'schedule_risks': self.check_schedule_risk()
        }
        
        return results
    
    def get_project_risk_summary(self, project_id: str) -> Dict:
        """
        获取项目风险摘要
        
        Args:
            project_id: 项目ID
            
        Returns:
            风险摘要字典
        """
        try:
            from pmsapp.models import RiskAlert as RiskAlertModel
            
            alerts = RiskAlertModel.objects.filter(project__project_id=project_id, is_resolved=False)
            
            high_count = alerts.filter(risk_level='high').count()
            medium_count = alerts.filter(risk_level='medium').count()
            low_count = alerts.filter(risk_level='low').count()
            
            overall_level = 'low'
            if high_count > 0:
                overall_level = 'high'
            elif medium_count > 0:
                overall_level = 'medium'
            elif low_count > 0:
                overall_level = 'low'
            
            return {
                'project_id': project_id,
                'overall_risk_level': overall_level,
                'risk_counts': {
                    'high': high_count,
                    'medium': medium_count,
                    'low': low_count,
                    'total': alerts.count()
                },
                'alerts': [a.to_dict() for a in alerts.order_by('-created_at')[:10]]
            }
        except Exception as e:
            logger.error(f"获取项目风险摘要失败: {e}")
            return {'error': str(e)}
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        标记预警为已解决
        
        Args:
            alert_id: 预警ID
            
        Returns:
            是否成功
        """
        try:
            from pmsapp.models import RiskAlert as RiskAlertModel
            
            RiskAlertModel.objects.filter(alert_id=alert_id).update(is_resolved=True)
            return True
        except Exception as e:
            logger.error(f"解决预警失败: {e}")
            return False
    
    def _save_alert(self, alert: RiskAlert):
        """保存预警到数据库"""
        try:
            from pmsapp.models import RiskAlert as RiskAlertModel, ProjectInfo
            
            project = ProjectInfo.objects.filter(project_id=alert.project_id).first()
            if not project:
                return
            
            exists = RiskAlertModel.objects.filter(alert_id=alert.alert_id).exists()
            if not exists:
                RiskAlertModel.objects.create(
                    alert_id=alert.alert_id,
                    project=project,
                    alert_type=alert.alert_type,
                    risk_level=alert.risk_level,
                    description=alert.description,
                    suggestion=alert.suggestion,
                    is_resolved=alert.is_resolved
                )
        except Exception as e:
            logger.warning(f"保存预警失败: {e}")


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.ai_agent = None
        self._init_ai()
    
    def _init_ai(self):
        """初始化AI代理"""
        try:
            from pmsapp.services.ai_agent import AIAgent
            self.ai_agent = AIAgent()
        except Exception as e:
            logger.warning(f"初始化AI代理失败: {e}")
    
    def generate_weekly(self, user_id: str, week_start: date = None, week_end: date = None) -> str:
        """
        生成周报
        
        Args:
            user_id: 用户ID
            week_start: 周开始日期，默认本周一
            week_end: 周结束日期，默认本周日
            
        Returns:
            生成的周报内容
        """
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        if week_end is None:
            week_end = week_start + timedelta(days=6)
        
        period_str = f"{week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}"
        
        return self._generate_report(user_id, 'weekly', period_str, week_start, week_end)
    
    def generate_monthly(self, user_id: str, year: int = None, month: int = None) -> str:
        """
        生成月报
        
        Args:
            user_id: 用户ID
            year: 年份，默认当前年
            month: 月份，默认当前月
            
        Returns:
            生成的月报内容
        """
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        period_str = f"{month_start.strftime('%Y-%m-%d')} 至 {month_end.strftime('%Y-%m-%d')}"
        
        return self._generate_report(user_id, 'monthly', period_str, month_start, month_end)
    
    def _generate_report(self, user_id: str, report_type: str, period_str: str, 
                         start_date: date, end_date: date) -> str:
        """内部报告生成方法"""
        try:
            from pmsapp.models import TaskInfo, UserInfo, WeeklySummary
            
            user = UserInfo.objects.filter(user_id=user_id).first()
            if not user:
                return "用户不存在"
            
            tasks = TaskInfo.objects.filter(
                task_owner=user,
                plan_start_date__lte=end_date,
                plan_end_date__gte=start_date
            )
            
            completed = tasks.filter(task_status='已完成').count()
            in_progress = tasks.filter(task_status='进行中').count()
            not_started = tasks.filter(task_status='未开始').count()
            total = tasks.count()
            
            completion_rate = (completed / total * 100) if total > 0 else 0
            
            task_details = []
            for task in tasks.order_by('-plan_end_date')[:10]:
                task_details.append({
                    'name': task.key_content_name,
                    'project': task.project.project_name,
                    'status': task.task_status,
                    'end_date': task.plan_end_date.strftime('%Y-%m-%d')
                })
            
            context_prompt = self._build_report_prompt(
                report_type, period_str, user.user_name,
                completed, in_progress, not_started, total, completion_rate,
                task_details
            )
            
            if self.ai_agent:
                try:
                    config = self.ai_agent.gateway.get_config() if self.ai_agent.gateway else None
                    if config:
                        response = self.ai_agent.chat(user_id, context_prompt)
                        report = response.content if hasattr(response, 'content') else str(response)
                        
                        self._save_summary(user, report_type, period_str, report, completed)
                        return report
                except Exception as e:
                    logger.warning(f"AI报告生成失败，使用简单报告: {e}")
            
            report = self._generate_simple_report(
                report_type, period_str, user.user_name,
                completed, in_progress, not_started, total, completion_rate,
                task_details
            )
            
            self._save_summary(user, report_type, period_str, report, completed)
            
            return report
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return f"报告生成失败: {str(e)}"
    
    def _build_report_prompt(self, report_type: str, period_str: str, user_name: str,
                            completed: int, in_progress: int, not_started: int,
                            total: int, completion_rate: float,
                            task_details: List[Dict]) -> str:
        """构建AI报告提示词"""
        report_type_cn = '周' if report_type == 'weekly' else '月'
        
        tasks_text = '\n'.join([
            f"- {t['name']} ({t['project']}) - {t['status']} - 截止{t['end_date']}"
            for t in task_details
        ]) if task_details else '暂无任务'
        
        prompt = f'''请根据以下信息生成{report_type_cn}工作报告：

统计周期：{period_str}
用户：{user_name}

任务统计：
- 总任务数：{total}
- 已完成：{completed}
- 进行中：{in_progress}
- 未开始：{not_started}
- 完成率：{completion_rate:.1f}%

任务详情：
{tasks_text}

请生成一份专业的{report_type_cn}工作报告，包含：
1. 工作总结（用中文）
2. 任务完成情况分析（用中文）
3. 存在的问题和挑战（用中文）
4. 下期工作计划（用中文）

请用中文回复，格式清晰。'''
        
        return prompt
    
    def _generate_simple_report(self, report_type: str, period_str: str, user_name: str,
                               completed: int, in_progress: int, not_started: int,
                               total: int, completion_rate: float,
                               task_details: List[Dict]) -> str:
        """生成简单文本报告"""
        report_type_cn = '周' if report_type == 'weekly' else '月'
        
        report = f'''
{report_type_cn}工作报告
{'=' * 30}
统计周期：{period_str}
用户：{user_name}

一、任务完成情况
----------------
- 总任务数：{total}
- 已完成：{completed}
- 进行中：{in_progress}
- 未开始：{not_started}
- 完成率：{completion_rate:.1f}%

二、工作总结
----------------
'''
        if completed > 0:
            report += f'本{report_type_cn}共完成{completed}项任务，'
            if completion_rate >= 80:
                report += '任务完成情况良好，'
            elif completion_rate >= 50:
                report += '任务完成情况一般，需要加快进度，'
            else:
                report += '任务完成率较低，需要加强执行力，'
        else:
            report += f'本{report_type_cn}暂无完成的任务，'
        
        if in_progress > 0:
            report += f'另有{in_progress}项任务正在进行中。'
        else:
            report += '。'
        
        report += f'\n\n三、存在的问题\n----------------\n'
        if completion_rate < 50:
            report += '- 任务完成率偏低，需要分析原因并改进\n'
        if in_progress > total * 0.5:
            report += '- 进行中任务较多，需要加快执行速度\n'
        if not report.endswith('\n'):
            report += '- 暂无明显问题\n'
        
        report += f'\n四、下期工作计划\n----------------\n'
        if in_progress > 0:
            report += f'- 继续推进{in_progress}项进行中的任务\n'
        if not_started > 0:
            report += f'- 启动{not_started}项计划任务\n'
        report += '- 合理安排时间，确保任务按时完成\n'
        
        if task_details:
            report += f'\n五、任务详情\n----------------\n'
            for i, task in enumerate(task_details[:5], 1):
                status_icon = '✓' if task['status'] == '已完成' else '○' if task['status'] == '进行中' else '□'
                report += f'{status_icon} {task["name"]}\n'
                report += f'   项目: {task["project"]} | 截止: {task["end_date"]}\n'
        
        return report
    
    def _save_summary(self, user, report_type: str, period_str: str, content: str, completed_count: int):
        """保存报告到数据库"""
        try:
            from pmsapp.models import WeeklySummary
            
            summary_id = f"SUMMARY-{date.today().strftime('%Y%m%d')}-{WeeklySummary.objects.count() + 1:04d}"
            
            completed_work = content
            next_week_plan = ''
            
            if '\n四、下期工作计划' in content:
                parts = content.split('\n四、下期工作计划')
                if len(parts) > 1:
                    next_week_plan = parts[1]
            
            WeeklySummary.objects.create(
                summary_id=summary_id,
                user_name=user,
                summary_week=period_str,
                completed_work=completed_work[:2000] if completed_work else '',
                next_week_plan=next_week_plan[:2000] if next_week_plan else '',
                completed_count=completed_count
            )
        except Exception as e:
            logger.warning(f"保存报告摘要失败: {e}")
    
    def stream_generate_weekly(self, user_id: str, week_start: date = None, week_end: date = None) -> Generator[str, None, None]:
        """
        流式生成周报
        
        Args:
            user_id: 用户ID
            week_start: 周开始日期
            week_end: 周结束日期
            
        Yields:
            流式报告内容
        """
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        if week_end is None:
            week_end = week_start + timedelta(days=6)
        
        period_str = f"{week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}"
        
        yield from self._stream_generate(user_id, 'weekly', period_str)
    
    def _stream_generate(self, user_id: str, report_type: str, period_str: str) -> Generator[str, None, None]:
        """流式生成报告"""
        try:
            from pmsapp.models import TaskInfo, UserInfo
            
            user = UserInfo.objects.filter(user_id=user_id).first()
            if not user:
                yield "用户不存在"
                return
            
            today = date.today()
            if report_type == 'weekly':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            else:
                start_date = today.replace(day=1)
                if today.month == 12:
                    end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            
            tasks = TaskInfo.objects.filter(
                task_owner=user,
                plan_start_date__lte=end_date,
                plan_end_date__gte=start_date
            )
            
            completed = tasks.filter(task_status='已完成').count()
            total = tasks.count()
            
            if not self.ai_agent:
                yield self._generate_simple_report(report_type, period_str, user.user_name, completed, 0, 0, total, 0, [])
                return
            
            prompt = f'生成{report_type == "weekly" and "周" or "月"}工作报告，主题：{period_str}'
            
            for chunk in self.ai_agent.stream_chat(user_id, prompt):
                yield chunk
        except Exception as e:
            logger.error(f"流式生成报告失败: {e}")
            yield f"报告生成失败: {str(e)}"
