import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('超级用户已创建: admin / admin123')
else:
    print('管理员用户已存在')

from pmsapp.models import UserInfo

if not UserInfo.objects.filter(user_name='admin').exists():
    UserInfo.objects.create(
        user_id='USER-001',
        user_name='admin',
        team_name='管理团队',
        contact_info='13800000000'
    )
    print('用户信息已创建')
else:
    print('用户信息已存在')
