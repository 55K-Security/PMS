import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings')
django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

# 创建超级管理员 sysadmin
if not User.objects.filter(username='sysadmin').exists():
    User.objects.create_superuser('sysadmin', 'sysadmin@example.com', 'SysAdmin@2024')
    print('Created superuser: sysadmin')
else:
    print('sysadmin already exists')

# 创建管理员 admin (不是超级用户，但可以访问管理后台)
if not User.objects.filter(username='admin').exists():
    admin_user = User.objects.create_user('admin', 'admin@example.com', 'Admin@2024')
    admin_user.is_staff = True
    admin_user.save()
    print('Created admin user: admin')
else:
    print('admin already exists')

# 确保pmsapp的权限给admin角色
from pmsapp.models import ProjectInfo, TaskInfo, BudgetCost, UserInfo

# 给admin用户添加所有pmsapp的权限
content_types = [
    ContentType.objects.get_for_model(ProjectInfo),
    ContentType.objects.get_for_model(TaskInfo),
    ContentType.objects.get_for_model(BudgetCost),
    ContentType.objects.get_for_model(UserInfo),
]

admin_user = User.objects.filter(username='admin').first()
if admin_user:
    for ct in content_types:
        perms = Permission.objects.filter(content_type=ct)
        admin_user.user_permissions.add(*perms)
    print('Added permissions to admin user')

print('\n=== User Accounts ===')
print('Super Admin: sysadmin / SysAdmin@2024')
print('Admin: admin / Admin@2024')
