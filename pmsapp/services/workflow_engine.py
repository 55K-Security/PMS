"""
工作流引擎 - 自动化业务流程执行
支持规则定义、触发检测、动作执行、日志记录
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from django.db.models import Q

logger = logging.getLogger(__name__)


class WorkflowRule:
    """工作流规则对象"""
    
    TRIGGER_TYPES = [
        'task_overdue',       # 任务逾期
        'task_completed',     # 任务完成
        'budget_exceeded',    # 预算超支
        'schedule_delayed',   # 进度延迟
        'daily',              # 每日触发
        'weekly',             # 每周触发
        'manual',             # 手动触发
    ]
    
    ACTION_TYPES = [
        'send_notification',  # 发送通知
        'create_reminder',    # 创建提醒
        'update_status',      # 更新状态
        'generate_report',    # 生成报告
        'call_ai',           # 调用AI
    ]
    
    def __init__(self, rule_id: str, rule_name: str, trigger_type: str, 
                 trigger_condition: Dict, action_type: str, action_config: Dict,
                 is_enabled: bool = True, created_by: str = None):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.trigger_type = trigger_type
        self.trigger_condition = trigger_condition
        self.action_type = action_type
        self.action_config = action_config
        self.is_enabled = is_enabled
        self.created_by = created_by
        self.created_at = datetime.now()
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowRule':
        """从字典创建规则对象"""
        return cls(
            rule_id=data.get('rule_id', ''),
            rule_name=data.get('rule_name', ''),
            trigger_type=data.get('trigger_type', 'manual'),
            trigger_condition=json.loads(data.get('trigger_condition', '{}')),
            action_type=data.get('action_type', 'send_notification'),
            action_config=json.loads(data.get('action_config', '{}')),
            is_enabled=data.get('is_enabled', True),
            created_by=data.get('created_by')
        )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'trigger_type': self.trigger_type,
            'trigger_condition': json.dumps(self.trigger_condition),
            'action_type': self.action_type,
            'action_config': json.dumps(self.action_config),
            'is_enabled': self.is_enabled,
            'created_by': self.created_by
        }


class ExecutionResult:
    """工作流执行结果"""
    
    def __init__(self, success: bool, message: str = '', data: Any = None):
        self.success = success
        self.message = message
        self.data = data
        self.executed_at = datetime.now()


class WorkflowEngine:
    """工作流自动化引擎"""
    
    def __init__(self):
        self.rules: List[WorkflowRule] = []
        self._action_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
        self._load_rules()
    
    def _register_default_handlers(self):
        """注册默认动作处理器"""
        self._action_handlers['send_notification'] = self._handle_send_notification
        self._action_handlers['create_reminder'] = self._handle_create_reminder
        self._action_handlers['update_status'] = self._handle_update_status
        self._action_handlers['generate_report'] = self._handle_generate_report
        self._action_handlers['call_ai'] = self._handle_call_ai
    
    def _load_rules(self):
        """从数据库加载规则"""
        try:
            from pmsapp.models import WorkflowRule as WorkflowRuleModel
            
            rules = WorkflowRuleModel.objects.filter(is_enabled=True)
            for r in rules:
                rule = WorkflowRule(
                    rule_id=r.rule_id,
                    rule_name=r.rule_name,
                    trigger_type=r.trigger_type,
                    trigger_condition=json.loads(r.trigger_condition) if r.trigger_condition else {},
                    action_type=r.action_type,
                    action_config=json.loads(r.action_config) if r.action_config else {},
                    is_enabled=r.is_enabled,
                    created_by=r.created_by.user_id if r.created_by else None
                )
                self.rules.append(rule)
        except Exception as e:
            logger.warning(f"加载工作流规则失败: {e}")
    
    def add_rule(self, rule: WorkflowRule) -> bool:
        """
        添加工作流规则
        
        Args:
            rule: 工作流规则对象
            
        Returns:
            是否添加成功
        """
        try:
            from pmsapp.models import WorkflowRule as WorkflowRuleModel, UserInfo
            
            if rule.rule_id:
                rule_exists = WorkflowRuleModel.objects.filter(rule_id=rule.rule_id).exists()
                if rule_exists:
                    return self.update_rule(rule)
            else:
                rule_count = WorkflowRuleModel.objects.count() + 1
                rule.rule_id = f"WF-{datetime.now().strftime('%Y%m%d')}-{rule_count:04d}"
            
            created_by = None
            if rule.created_by:
                created_by = UserInfo.objects.filter(user_id=rule.created_by).first()
            
            WorkflowRuleModel.objects.create(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                trigger_type=rule.trigger_type,
                trigger_condition=json.dumps(rule.trigger_condition),
                action_type=rule.action_type,
                action_config=json.dumps(rule.action_config),
                is_enabled=rule.is_enabled,
                created_by=created_by
            )
            
            self.rules.append(rule)
            return True
        except Exception as e:
            logger.error(f"添加工作流规则失败: {e}")
            return False
    
    def update_rule(self, rule: WorkflowRule) -> bool:
        """
        更新工作流规则
        
        Args:
            rule: 工作流规则对象
            
        Returns:
            是否更新成功
        """
        try:
            from pmsapp.models import WorkflowRule as WorkflowRuleModel
            
            WorkflowRuleModel.objects.filter(rule_id=rule.rule_id).update(
                rule_name=rule.rule_name,
                trigger_type=rule.trigger_type,
                trigger_condition=json.dumps(rule.trigger_condition),
                action_type=rule.action_type,
                action_config=json.dumps(rule.action_config),
                is_enabled=rule.is_enabled
            )
            
            for i, r in enumerate(self.rules):
                if r.rule_id == rule.rule_id:
                    self.rules[i] = rule
                    break
            
            return True
        except Exception as e:
            logger.error(f"更新工作流规则失败: {e}")
            return False
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        删除工作流规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            是否删除成功
        """
        try:
            from pmsapp.models import WorkflowRule as WorkflowRuleModel
            
            WorkflowRuleModel.objects.filter(rule_id=rule_id).delete()
            self.rules = [r for r in self.rules if r.rule_id != rule_id]
            return True
        except Exception as e:
            logger.error(f"删除工作流规则失败: {e}")
            return False
    
    def get_rules(self, trigger_type: str = None) -> List[WorkflowRule]:
        """
        获取工作流规则列表
        
        Args:
            trigger_type: 可选，按触发类型过滤
            
        Returns:
            规则列表
        """
        if trigger_type:
            return [r for r in self.rules if r.trigger_type == trigger_type]
        return self.rules
    
    def execute(self, trigger: str, context: Dict) -> ExecutionResult:
        """
        执行触发的工作流
        
        Args:
            trigger: 触发器标识
            context: 上下文数据
            
        Returns:
            执行结果
        """
        matched_rules = [r for r in self.rules if r.trigger_type == trigger and r.is_enabled]
        
        if not matched_rules:
            return ExecutionResult(True, "没有匹配的工作流规则")
        
        results = []
        for rule in matched_rules:
            if self._check_condition(rule, context):
                result = self._execute_action(rule, context)
                self._log_execution(rule, context, result)
                results.append(result)
        
        if results:
            success = all(r.success for r in results)
            message = f"执行了{len(results)}个工作流"
            return ExecutionResult(success, message, results)
        else:
            return ExecutionResult(True, "没有满足条件的规则")
    
    def _check_condition(self, rule: WorkflowRule, context: Dict) -> bool:
        """检查触发条件是否满足"""
        condition = rule.trigger_condition
        
        if rule.trigger_type == 'task_overdue':
            days = condition.get('days', 3)
            return context.get('overdue_days', 0) >= days
        
        elif rule.trigger_type == 'budget_exceeded':
            threshold = condition.get('threshold', 80)
            return context.get('budget_ratio', 0) >= threshold
        
        elif rule.trigger_type == 'schedule_delayed':
            threshold = condition.get('threshold', 15)
            return context.get('delay_percent', 0) >= threshold
        
        return True
    
    def _execute_action(self, rule: WorkflowRule, context: Dict) -> ExecutionResult:
        """执行动作"""
        handler = self._action_handlers.get(rule.action_type)
        if not handler:
            return ExecutionResult(False, f"未知的动作类型: {rule.action_type}")
        
        try:
            return handler(rule, context)
        except Exception as e:
            logger.error(f"执行动作失败: {e}")
            return ExecutionResult(False, f"执行失败: {str(e)}")
    
    def _handle_send_notification(self, rule: WorkflowRule, context: Dict) -> ExecutionResult:
        """发送通知"""
        try:
            notification_type = rule.action_config.get('type', 'system')
            message = rule.action_config.get('message', '您有一条新通知')
            
            message = message.format(**context)
            
            logger.info(f"发送通知: {notification_type} - {message}")
            
            return ExecutionResult(True, "通知已发送", {'type': notification_type, 'message': message})
        except Exception as e:
            return ExecutionResult(False, f"发送通知失败: {str(e)}")
    
    def _handle_create_reminder(self, rule: WorkflowRule, context: Dict) -> ExecutionResult:
        """创建提醒"""
        try:
            from pmsapp.models import DailyReminder, UserInfo
            
            user_id = context.get('user_id')
            project_id = context.get('project_id')
            content = rule.action_config.get('content', '请注意此任务').format(**context)
            
            user = UserInfo.objects.filter(user_id=user_id).first()
            if not user:
                return ExecutionResult(False, "用户不存在")
            
            reminder_count = DailyReminder.objects.count() + 1
            reminder_id = f"REMINDER-{datetime.now().strftime('%Y%m%d')}-{reminder_count:04d}"
            
            DailyReminder.objects.create(
                reminder_id=reminder_id,
                reminder_date=datetime.now().date(),
                user_name=user,
                project_id=project_id,
                project_name=context.get('project_name', ''),
                key_content_name=content,
                task_type='周期内未完成',
                task_status='未开始'
            )
            
            return ExecutionResult(True, "提醒已创建")
        except Exception as e:
            logger.error(f"创建提醒失败: {e}")
            return ExecutionResult(False, f"创建提醒失败: {str(e)}")
    
    def _handle_update_status(self, rule: WorkflowRule, context: Dict) -> ExecutionResult:
        """更新状态"""
        try:
            from pmsapp.models import ProjectInfo, TaskInfo
            
            target_type = rule.action_config.get('target_type')
            target_id = rule.action_config.get('target_id')
            new_status = rule.action_config.get('status')
            
            if target_type == 'project':
                ProjectInfo.objects.filter(project_id=target_id).update(project_status=new_status)
            elif target_type == 'task':
                TaskInfo.objects.filter(task_id=target_id).update(task_status=new_status)
            
            return ExecutionResult(True, f"状态已更新为{new_status}")
        except Exception as e:
            return ExecutionResult(False, f"更新状态失败: {str(e)}")
    
    def _handle_generate_report(self, rule: WorkflowRule, context: Dict) -> ExecutionResult:
        """生成报告"""
        try:
            from pmsapp.services.ai_agent import AIAgent
            
            report_type = rule.action_config.get('report_type', 'weekly')
            user_id = context.get('user_id')
            
            agent = AIAgent()
            report = agent.generate_report(user_id, report_type)
            
            return ExecutionResult(True, "报告已生成", {'report': report})
        except Exception as e:
            return ExecutionResult(False, f"生成报告失败: {str(e)}")
    
    def _handle_call_ai(self, rule: WorkflowRule, context: Dict) -> ExecutionResult:
        """调用AI"""
        try:
            from pmsapp.services.ai_agent import AIAgent
            
            prompt = rule.action_config.get('prompt', '').format(**context)
            
            agent = AIAgent()
            response = agent.chat(context.get('user_id', 'system'), prompt)
            
            return ExecutionResult(True, "AI响应已生成", {'response': response.content})
        except Exception as e:
            return ExecutionResult(False, f"AI调用失败: {str(e)}")
    
    def _log_execution(self, rule: WorkflowRule, context: Dict, result: ExecutionResult):
        """记录执行日志"""
        try:
            from pmsapp.models import WorkflowLog, WorkflowRule as WorkflowRuleModel
            
            rule_model = WorkflowRuleModel.objects.filter(rule_id=rule.rule_id).first()
            
            log_count = WorkflowLog.objects.count() + 1
            log_id = f"WFL-{datetime.now().strftime('%Y%m%d')}-{log_count:04d}"
            
            WorkflowLog.objects.create(
                log_id=log_id,
                rule=rule_model,
                status='success' if result.success else 'failed',
                trigger_data=json.dumps(context),
                result=result.message,
                error_message=str(result.data) if not result.success else ''
            )
        except Exception as e:
            logger.warning(f"记录执行日志失败: {e}")
    
    def get_execution_log(self, rule_id: str = None, limit: int = 50) -> List[Dict]:
        """
        获取工作流执行日志
        
        Args:
            rule_id: 可选，按规则ID过滤
            limit: 返回条数限制
            
        Returns:
            日志列表
        """
        try:
            from pmsapp.models import WorkflowLog
            
            query = WorkflowLog.objects.all()
            if rule_id:
                query = query.filter(rule__rule_id=rule_id)
            
            logs = query.order_by('-executed_at')[:limit]
            
            return [
                {
                    'log_id': log.log_id,
                    'rule_id': log.rule.rule_id if log.rule else None,
                    'rule_name': log.rule.rule_name if log.rule else None,
                    'status': log.status,
                    'trigger_data': log.trigger_data,
                    'result': log.result,
                    'error_message': log.error_message,
                    'executed_at': log.executed_at.strftime('%Y-%m-%d %H:%M:%S') if log.executed_at else None
                }
                for log in logs
            ]
        except Exception as e:
            logger.error(f"获取执行日志失败: {e}")
            return []
    
    def trigger_check(self):
        """触发器检测 - 定期检查是否需要触发工作流"""
        try:
            from pmsapp.models import TaskInfo, ProjectInfo, BudgetCost
            from datetime import date
            
            overdue_tasks = TaskInfo.objects.filter(
                plan_end_date__lt=date.today(),
                task_status__in=['进行中', '未开始']
            )
            
            for task in overdue_tasks:
                overdue_days = (date.today() - task.plan_end_date).days
                context = {
                    'task_id': task.task_id,
                    'project_id': task.project.project_id,
                    'project_name': task.project.project_name,
                    'user_id': task.task_owner.user_id,
                    'user_name': task.task_owner.user_name,
                    'overdue_days': overdue_days
                }
                self.execute('task_overdue', context)
            
            budgets = BudgetCost.objects.filter(remaining_budget__lt=0)
            for budget in budgets:
                if budget.total_budget > 0:
                    ratio = (budget.total_cost / budget.total_budget) * 100
                    context = {
                        'project_id': budget.project.project_id,
                        'project_name': budget.project_name,
                        'user_id': budget.project.project_manager.user_id if hasattr(budget.project, 'project_manager') else None,
                        'budget_ratio': ratio
                    }
                    self.execute('budget_exceeded', context)
        except Exception as e:
            logger.error(f"触发器检测失败: {e}")
