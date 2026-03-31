from django.urls import path
from pmsapp import views

urlpatterns = [
    # 项目管理
    path('list/', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('edit/<str:project_id>/', views.project_edit, name='project_edit'),
    path('delete/<str:project_id>/', views.project_delete, name='project_delete'),
    path('gantt/', views.gantt_view, name='gantt_view'),
    path('api/tasks/<str:project_id>/', views.api_get_tasks_by_project, name='api_get_tasks_by_project'),
    path('api/update-progress/<str:project_id>/', views.api_update_project_progress, name='api_update_project_progress'),
    
    # 任务管理
    path('task/list/', views.task_list, name='task_list'),
    path('task/create/', views.task_create, name='task_create'),
    path('task/edit/<str:task_id>/', views.task_edit, name='task_edit'),
    path('task/delete/<str:task_id>/', views.task_delete, name='task_delete'),
    
    # 预算成本
    path('budget/list/', views.budget_list, name='budget_list'),
    path('budget/create/', views.budget_create, name='budget_create'),
    path('budget/edit/<str:budget_id>/', views.budget_edit, name='budget_edit'),
    
    # 团队管理
    path('user/list/', views.user_list, name='user_list'),
    path('team/create/', views.team_create, name='team_create'),
    path('team/edit/<str:team_id>/', views.team_edit, name='team_edit'),
    path('team/delete/<str:team_id>/', views.team_delete, name='team_delete'),
    
    # 日待办
    path('reminder/list/', views.reminder_list, name='reminder_list'),
    
    # 周计划
    path('weekly/plan_list/', views.weekly_plan_list, name='weekly_plan_list'),
    path('weekly/plan_create/', views.weekly_plan_create, name='weekly_plan_create'),
    path('weekly/plan_edit/<str:plan_id>/', views.weekly_plan_edit, name='weekly_plan_edit'),
    path('weekly/plan_delete/<str:plan_id>/', views.weekly_plan_delete, name='weekly_plan_delete'),
    
    # 四象限
    path('quadrant/list/', views.quadrant_list, name='quadrant_list'),
    
    # 周总结
    path('summary/list/', views.summary_list, name='summary_list'),
    path('summary/create/', views.summary_create, name='summary_create'),
    
    # 系统设置
    path('settings/', views.settings_view, name='settings'),
    path('settings/profile/', views.settings_profile, name='settings_profile'),
    path('settings/password/', views.settings_password, name='settings_password'),
    path('settings/ai/', views.settings_ai, name='settings_ai'),
    path('settings/email/', views.settings_email, name='settings_email'),
    path('settings/security/', views.settings_security, name='settings_security'),
    path('settings/ui_customize/', views.ui_customize, name='ui_customize'),
    path('api/ai-summary/', views.ai_generate_summary, name='ai_generate_summary'),
    # AI功能页面路由
    path('ai/', views.ai_dashboard, name='ai_dashboard'),
    path('ai/chat/', views.ai_chat_page, name='ai_chat'),
    path('ai/risks/', views.ai_risks_page, name='ai_risks'),
    path('ai/workflow/', views.workflow_rules_page, name='workflow_rules'),
    # AI API路由
    path('api/ai/chat/', views.ai_chat_api, name='ai_chat_api'),
    path('api/ai/chat/history/', views.ai_chat_history_api, name='ai_chat_history_api'),
    path('api/ai/chat/clear/', views.ai_chat_clear_api, name='ai_chat_clear_api'),
    path('api/ai/config/', views.ai_config_api, name='ai_config_api'),
    path('api/ai/config/validate/', views.ai_config_validate_api, name='ai_config_validate_api'),
    path('api/ai/analyze/risk/', views.ai_analyze_risk_api, name='ai_analyze_risk_api'),
    path('api/ai/analyze/report/', views.ai_generate_report_api, name='ai_generate_report_api'),
    path('api/ai/recommend/task/', views.ai_recommend_task_api, name='ai_recommend_task_api'),
    path('api/risks/alerts/', views.risk_alerts_api, name='risk_alerts_api'),
    path('api/risks/check/', views.risk_check_api, name='risk_check_api'),
    path('api/workflow/rules/', views.workflow_rules_api, name='workflow_rules_api'),
    path('api/workflow/logs/', views.workflow_logs_api, name='workflow_logs_api'),
    # 系统版本升级
    path('settings/version_upgrade/', views.version_upgrade, name='version_upgrade'),
    path('settings/logs_upgrade/', views.logs_upgrade, name='logs_upgrade'),
    path('settings/logs_upgrade/export/', views.logs_upgrade_export, name='logs_upgrade_export'),
    path('settings/logs_upgrade/export_excel/', views.logs_upgrade_export_excel, name='logs_upgrade_export_excel'),
    path('settings/logs_system/', views.logs_system, name='logs_system'),
    # 系统监控
    path('monitor/', views.system_monitor, name='system_monitor'),
    # 实时动态看板大屏
    path('dashboard-big/', views.dashboard_big, name='dashboard_big'),
    # 任务提醒统计
    path('api/reminder-counts/', views.system_reminder_counts, name='system_reminder_counts'),
    
    # 文件管理
    path('files/', views.file_list, name='file_list'),
    path('files/upload/', views.file_upload, name='file_upload'),
    path('files/delete/<int:file_id>/', views.file_delete, name='file_delete'),
    path('files/download/<int:file_id>/', views.file_download, name='file_download'),
    
    # 用户管理（管理员）
    path('admin-user/', views.admin_user_list, name='admin_user_list'),
    path('admin-user/create/', views.admin_user_create, name='admin_user_create'),
    path('admin-user/edit/<int:user_id>/', views.admin_user_edit, name='admin_user_edit'),
    path('admin-user/delete/<int:user_id>/', views.admin_user_delete, name='admin_user_delete'),
    path('admin-user/reset-password/<int:user_id>/', views.admin_user_reset_password, name='admin_user_reset_password'),
    
    # 告警中心
    path('alarm/', views.alarm_list, name='alarm_list'),
    path('api/send-alarm-email/', views.send_alarm_email, name='send_alarm_email'),
    
    # API
    path('api/sync_reminders/', views.api_sync_reminders, name='api_sync_reminders'),
    path('api/sync_quadrants/', views.api_sync_quadrants, name='api_sync_quadrants'),
    path('api/monitor-data/', views.api_monitor_data, name='api_monitor_data'),
    
    # 帮助文档
    path('help/', views.help_index, name='help_index'),
]
