from django.db import models


class UserInfo(models.Model):
    """人员信息表"""
    user_id = models.CharField(max_length=32, primary_key=True, verbose_name='用户ID')
    user_name = models.CharField(max_length=32, unique=True, verbose_name='用户名')
    responsible_count = models.IntegerField(default=0, verbose_name='负责关键内容数量')
    completed_task_count = models.IntegerField(default=0, verbose_name='已完成任务数')
    in_progress_task_count = models.IntegerField(default=0, verbose_name='进行中任务数')
    not_started_task_count = models.IntegerField(default=0, verbose_name='未开始任务数')
    team_name = models.CharField(max_length=32, blank=True, null=True, verbose_name='所属团队')
    contact_info = models.CharField(max_length=32, blank=True, null=True, verbose_name='联系方式')

    class Meta:
        db_table = 't_user_info'
        verbose_name = '人员信息'
        verbose_name_plural = '人员信息'

    def __str__(self):
        return self.user_name


class ProjectInfo(models.Model):
    """项目信息表"""
    STATUS_CHOICES = [
        ('未开始', '未开始'),
        ('进行中', '进行中'),
        ('已完成', '已完成'),
        ('逾期未完结', '逾期未完结'),
    ]

    project_id = models.CharField(max_length=32, primary_key=True, verbose_name='项目ID')
    project_name = models.CharField(max_length=64, unique=True, verbose_name='项目名称')
    project_manager = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='managed_projects', verbose_name='负责人')
    start_date = models.DateField(verbose_name='开始时间')
    end_date = models.DateField(verbose_name='结束时间')
    project_cycle = models.IntegerField(default=0, verbose_name='项目周期')
    key_content_count = models.IntegerField(default=0, verbose_name='关键内容数量')
    completed_count = models.IntegerField(default=0, verbose_name='已完成数量')
    in_progress_count = models.IntegerField(default=0, verbose_name='进行中数量')
    not_started_count = models.IntegerField(default=0, verbose_name='未开始数量')
    completion_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='完成进度')
    project_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='未开始', verbose_name='项目状态')
    milestone_length = models.IntegerField(blank=True, null=True, verbose_name='里程碑项目长度')
    milestone_completed_length = models.DecimalField(max_digits=5, decimal_places=1, default=0.0, verbose_name='里程碑完成长度')
    milestone_height = models.IntegerField(blank=True, null=True, verbose_name='里程碑项目高度')
    remark = models.TextField(blank=True, null=True, verbose_name='备注说明')

    class Meta:
        db_table = 't_project_info'
        verbose_name = '项目信息'
        verbose_name_plural = '项目信息'
        ordering = ['-start_date']

    def __str__(self):
        return self.project_name

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.project_cycle = (self.end_date - self.start_date).days
        if self.key_content_count > 0:
            self.completion_progress = round((self.completed_count / self.key_content_count) * 100, 2)
        else:
            self.completion_progress = 0
        super().save(*args, **kwargs)


class TaskInfo(models.Model):
    """任务信息表"""
    PRIORITY_CHOICES = [
        ('优先级1', '优先级1（最高）'),
        ('优先级2', '优先级2'),
        ('优先级3', '优先级3'),
        ('优先级4', '优先级4（最低）'),
    ]
    STATUS_CHOICES = [
        ('已完成', '已完成'),
        ('进行中', '进行中'),
        ('未开始', '未开始'),
    ]

    task_id = models.CharField(max_length=32, primary_key=True, verbose_name='任务ID')
    project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE, related_name='tasks', verbose_name='项目ID')
    key_content_name = models.CharField(max_length=64, verbose_name='关键内容名称')
    priority_level = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default='优先级3', verbose_name='紧急程度')
    task_owner = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='tasks', verbose_name='负责人')
    plan_start_date = models.DateField(verbose_name='计划开始时间')
    plan_end_date = models.DateField(verbose_name='计划结束时间')
    task_cycle = models.IntegerField(verbose_name='任务周期')
    time_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='时间进度')
    task_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='未开始', verbose_name='任务状态')
    actual_complete_date = models.DateField(blank=True, null=True, verbose_name='实际完成时间')
    completion_reminder = models.CharField(max_length=64, blank=True, null=True, verbose_name='完成提醒')
    completion_remark = models.TextField(blank=True, null=True, verbose_name='完成情况备注')

    class Meta:
        db_table = 't_task_info'
        verbose_name = '任务信息'
        verbose_name_plural = '任务信息'
        ordering = ['priority_level', 'plan_end_date']

    def __str__(self):
        return f"{self.project.project_name} - {self.key_content_name}"

    def save(self, *args, **kwargs):
        if self.plan_start_date and self.plan_end_date:
            self.task_cycle = (self.plan_end_date - self.plan_start_date).days
        super().save(*args, **kwargs)


class BudgetCost(models.Model):
    """预算成本表"""
    budget_id = models.CharField(max_length=32, primary_key=True, verbose_name='预算ID')
    project = models.OneToOneField(ProjectInfo, on_delete=models.CASCADE, related_name='budget', verbose_name='项目ID')
    project_name = models.CharField(max_length=64, verbose_name='项目名称')
    project_manager = models.CharField(max_length=32, verbose_name='负责人')
    start_date = models.DateField(verbose_name='开始时间')
    end_date = models.DateField(verbose_name='结束时间')
    workday_count = models.IntegerField(verbose_name='工作日天数')
    participant_count = models.IntegerField(verbose_name='投入人数')
    total_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='总预算金额')
    personnel_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='人员成本')
    rnd_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='研发成本')
    design_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='设计成本')
    travel_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='差旅成本')
    marketing_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='市场推广成本')
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='总成本')
    remaining_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='剩余预算金额')
    cost_remark = models.TextField(blank=True, null=True, verbose_name='成本说明')
    cost_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='成本分类占比')

    class Meta:
        db_table = 't_budget_cost'
        verbose_name = '预算成本'
        verbose_name_plural = '预算成本'

    def __str__(self):
        return f"{self.project_name} - 预算"

    def save(self, *args, **kwargs):
        self.total_cost = (self.personnel_cost or 0) + (self.rnd_cost or 0) + \
                          (self.design_cost or 0) + (self.travel_cost or 0) + (self.marketing_cost or 0)
        self.remaining_budget = (self.total_budget or 0) - self.total_cost
        if self.total_cost > 0 and self.total_budget > 0:
            self.cost_ratio = round((self.total_cost / self.total_budget) * 100, 2)
        super().save(*args, **kwargs)


class DailyReminder(models.Model):
    """日待办提醒表"""
    TASK_TYPE_CHOICES = [
        ('今日开始', '今日开始'),
        ('今日截止', '今日截止'),
        ('已逾期', '已逾期'),
        ('周期内未完成', '周期内未完成'),
    ]
    STATUS_CHOICES = [
        ('已完成', '已完成'),
        ('进行中', '进行中'),
        ('未开始', '未开始'),
    ]

    reminder_id = models.CharField(max_length=32, primary_key=True, verbose_name='提醒ID')
    reminder_date = models.DateField(verbose_name='日期')
    user_name = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='reminders', verbose_name='用户名')
    project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE, verbose_name='项目ID')
    project_name = models.CharField(max_length=64, verbose_name='项目名称')
    key_content_name = models.CharField(max_length=64, verbose_name='关键内容名称')
    task_type = models.CharField(max_length=16, choices=TASK_TYPE_CHOICES, verbose_name='任务类型')
    task_status = models.CharField(max_length=16, choices=STATUS_CHOICES, verbose_name='任务状态')
    overdue_days = models.IntegerField(default=0, verbose_name='逾期天数')

    class Meta:
        db_table = 't_daily_reminder'
        verbose_name = '日待办提醒'
        verbose_name_plural = '日待办提醒'
        ordering = ['-reminder_date', 'task_type']

    def __str__(self):
        return f"{self.reminder_date} - {self.user_name.user_name} - {self.key_content_name}"


class WeeklyPlan(models.Model):
    """周工作计划表"""
    plan_id = models.CharField(max_length=32, primary_key=True, verbose_name='计划ID')
    user_name = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='weekly_plans', verbose_name='用户名')
    plan_week = models.CharField(max_length=16, verbose_name='计划周期')
    monday_task = models.TextField(blank=True, null=True, verbose_name='星期一任务')
    tuesday_task = models.TextField(blank=True, null=True, verbose_name='星期二任务')
    wednesday_task = models.TextField(blank=True, null=True, verbose_name='星期三任务')
    thursday_task = models.TextField(blank=True, null=True, verbose_name='星期四任务')
    friday_task = models.TextField(blank=True, null=True, verbose_name='星期五任务')
    saturday_task = models.TextField(blank=True, null=True, verbose_name='星期六任务')
    sunday_task = models.TextField(blank=True, null=True, verbose_name='星期日任务')
    completed_count = models.IntegerField(default=0, verbose_name='已完成任务数')
    in_progress_count = models.IntegerField(default=0, verbose_name='进行中任务数')
    not_started_count = models.IntegerField(default=0, verbose_name='未开始任务数')

    class Meta:
        db_table = 't_weekly_plan'
        verbose_name = '周工作计划'
        verbose_name_plural = '周工作计划'
        ordering = ['-plan_week']

    def __str__(self):
        return f"{self.user_name.user_name} - {self.plan_week}"


class QuadrantTask(models.Model):
    """四象限任务表"""
    STAT_CYCLE_CHOICES = [
        ('今日', '今日'),
        ('本周', '本周'),
        ('本月', '本月'),
    ]
    QUADRANT_CHOICES = [
        ('优先级1-重要紧急', '重要紧急'),
        ('优先级2-重要不紧急', '重要不紧急'),
        ('优先级3-紧急不重要', '紧急不重要'),
        ('优先级4-不紧急不重要', '不紧急不重要'),
    ]
    STATUS_CHOICES = [
        ('已完成', '已完成'),
        ('进行中', '进行中'),
        ('未开始', '未开始'),
    ]

    quadrant_id = models.CharField(max_length=32, primary_key=True, verbose_name='象限ID')
    user_name = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='quadrant_tasks', verbose_name='用户名')
    stat_cycle = models.CharField(max_length=16, choices=STAT_CYCLE_CHOICES, default='本月', verbose_name='统计周期')
    quadrant_type = models.CharField(max_length=32, choices=QUADRANT_CHOICES, verbose_name='象限类型')
    project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE, verbose_name='项目ID')
    project_name = models.CharField(max_length=64, verbose_name='项目名称')
    key_content_name = models.CharField(max_length=64, verbose_name='关键内容名称')
    task_owner = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='owned_quadrant_tasks', verbose_name='负责人')
    end_date = models.DateField(verbose_name='结束时间')
    task_status = models.CharField(max_length=16, choices=STATUS_CHOICES, verbose_name='任务状态')

    class Meta:
        db_table = 't_quadrant_task'
        verbose_name = '四象限任务'
        verbose_name_plural = '四象限任务'

    def __str__(self):
        return f"{self.quadrant_type} - {self.key_content_name}"


class WeeklySummary(models.Model):
    """周工作总结表"""
    summary_id = models.CharField(max_length=32, primary_key=True, verbose_name='总结ID')
    user_name = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='weekly_summaries', verbose_name='用户名')
    summary_week = models.CharField(max_length=16, verbose_name='总结周期')
    completed_work = models.TextField(blank=True, null=True, verbose_name='本周已完成工作')
    uncompleted_work = models.TextField(blank=True, null=True, verbose_name='本周截止未完成工作')
    next_week_plan = models.TextField(blank=True, null=True, verbose_name='下周工作计划')
    problems_suggestions = models.TextField(blank=True, null=True, verbose_name='问题与建议')
    completed_count = models.IntegerField(default=0, verbose_name='已完成任务数')

    class Meta:
        db_table = 't_weekly_summary'
        verbose_name = '周工作总结'
        verbose_name_plural = '周工作总结'
        ordering = ['-summary_week']

    def __str__(self):
        return f"{self.user_name.user_name} - {self.summary_week}"


class ProjectFile(models.Model):
    """项目文件表"""
    file_name = models.CharField(max_length=255, verbose_name='文件名')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    file_size = models.BigIntegerField(verbose_name='文件大小')
    description = models.TextField(blank=True, null=True, verbose_name='文件描述')
    uploaded_by = models.ForeignKey(UserInfo, on_delete=models.SET_NULL, null=True, verbose_name='上传人')
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    
    class Meta:
        db_table = 't_project_file'
        verbose_name = '项目文件'
        verbose_name_plural = '项目文件'
        ordering = ['-upload_date']
    
    def __str__(self):
        return self.file_name
    
    def get_file_size_display(self):
        """格式化文件大小"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


class SystemSettings(models.Model):
    """系统设置"""
    SETTING_TYPES = [
        ('ai', 'AI配置'),
        ('email', '邮件配置'),
        ('security', '安全设置'),
    ]
    
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, verbose_name='设置类型')
    setting_key = models.CharField(max_length=64, verbose_name='设置键')
    setting_value = models.TextField(blank=True, verbose_name='设置值')
    description = models.CharField(max_length=128, blank=True, verbose_name='描述')
    is_enabled = models.BooleanField(default=False, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 't_system_settings'
        verbose_name = '系统设置'
        verbose_name_plural = '系统设置'
        unique_together = [['setting_type', 'setting_key']]
    
    def __str__(self):
        return f"{self.get_setting_type_display()} - {self.setting_key}"

class UpgradeLog(models.Model):
    """系统升级日志"""
    log_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserInfo, on_delete=models.SET_NULL, null=True, related_name='upgrade_logs')
    upload_time = models.DateTimeField(auto_now_add=True)
    patch_file_name = models.CharField(max_length=255, blank=True, null=True)
    upgrade_file_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=32, default='SUCCESS')
    notes = models.TextField(blank=True, null=True)
    # additional audit fields
    action_source = models.CharField(max_length=64, default='web')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    upgrade_version = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        db_table = 't_upgrade_log'
        verbose_name = '升级日志'
        verbose_name_plural = '升级日志'

    def __str__(self):
        return f"{self.log_id} {self.upload_time} {self.status}"


class TeamGroup(models.Model):
    """团队组"""
    team_id = models.CharField(max_length=32, primary_key=True, verbose_name='团队ID')
    team_name = models.CharField(max_length=64, unique=True, verbose_name='团队名称')
    members = models.ManyToManyField(UserInfo, related_name='teams', blank=True, verbose_name='成员')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    remark = models.TextField(blank=True, verbose_name='备注')
    
    class Meta:
        db_table = 't_team_group'
        verbose_name = '团队组'
        verbose_name_plural = '团队组'
    
    def __str__(self):
        return self.team_name


class AIChatHistory(models.Model):
    """AI对话历史表"""
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', 'AI助手'),
        ('system', '系统'),
    ]
    
    history_id = models.CharField(max_length=64, primary_key=True, verbose_name='历史记录ID')
    user = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='ai_chat_history', verbose_name='用户')
    session_id = models.CharField(max_length=64, verbose_name='会话ID')
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, verbose_name='角色')
    content = models.TextField(verbose_name='消息内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 't_ai_chat_history'
        verbose_name = 'AI对话历史'
        verbose_name_plural = 'AI对话历史'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'session_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.user_name} - {self.role} - {self.created_at}"


class WorkflowRule(models.Model):
    """工作流规则表"""
    TRIGGER_TYPES = [
        ('task_overdue', '任务逾期'),
        ('task_completed', '任务完成'),
        ('budget_exceeded', '预算超支'),
        ('schedule_delayed', '进度延迟'),
        ('daily', '每日触发'),
        ('weekly', '每周触发'),
        ('manual', '手动触发'),
    ]
    
    ACTION_TYPES = [
        ('send_notification', '发送通知'),
        ('create_reminder', '创建提醒'),
        ('update_status', '更新状态'),
        ('generate_report', '生成报告'),
        ('call_ai', '调用AI'),
    ]
    
    rule_id = models.CharField(max_length=32, primary_key=True, verbose_name='规则ID')
    rule_name = models.CharField(max_length=64, verbose_name='规则名称')
    trigger_type = models.CharField(max_length=32, choices=TRIGGER_TYPES, verbose_name='触发类型')
    trigger_condition = models.TextField(blank=True, null=True, verbose_name='触发条件')
    action_type = models.CharField(max_length=32, choices=ACTION_TYPES, verbose_name='动作类型')
    action_config = models.TextField(blank=True, null=True, verbose_name='动作配置')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(UserInfo, on_delete=models.SET_NULL, null=True, related_name='created_workflow_rules', verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 't_workflow_rule'
        verbose_name = '工作流规则'
        verbose_name_plural = '工作流规则'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rule_name} ({self.get_trigger_type_display()})"


class WorkflowLog(models.Model):
    """工作流执行日志表"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    log_id = models.CharField(max_length=32, primary_key=True, verbose_name='日志ID')
    rule = models.ForeignKey(WorkflowRule, on_delete=models.SET_NULL, null=True, related_name='execution_logs', verbose_name='关联规则')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending', verbose_name='执行状态')
    trigger_data = models.TextField(blank=True, null=True, verbose_name='触发数据')
    result = models.TextField(blank=True, null=True, verbose_name='执行结果')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name='执行时间')
    
    class Meta:
        db_table = 't_workflow_log'
        verbose_name = '工作流日志'
        verbose_name_plural = '工作流日志'
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['rule', 'executed_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.log_id} - {self.rule.rule_name if self.rule else 'N/A'} - {self.status}"


class RiskAlert(models.Model):
    """风险预警表"""
    RISK_LEVEL_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    ]
    
    ALERT_TYPES = [
        ('task_overdue', '任务逾期'),
        ('budget_exceeded', '预算超支'),
        ('schedule_delayed', '进度延迟'),
    ]
    
    alert_id = models.CharField(max_length=64, primary_key=True, verbose_name='预警ID')
    project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE, related_name='risk_alerts', verbose_name='项目')
    alert_type = models.CharField(max_length=32, choices=ALERT_TYPES, verbose_name='预警类型')
    risk_level = models.CharField(max_length=16, choices=RISK_LEVEL_CHOICES, default='medium', verbose_name='风险等级')
    description = models.TextField(verbose_name='描述')
    suggestion = models.TextField(blank=True, null=True, verbose_name='建议')
    is_resolved = models.BooleanField(default=False, verbose_name='是否已解决')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name='解决时间')
    
    class Meta:
        db_table = 't_risk_alert'
        verbose_name = '风险预警'
        verbose_name_plural = '风险预警'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'is_resolved']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.project.project_name} - {self.get_risk_level_display()} - {self.get_alert_type_display()}"
