from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.contrib.auth import authenticate, login, logout
import os
import logging
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from datetime import datetime, date, timedelta
from decimal import Decimal
import random
import string
import json
import io
import base64

logger = logging.getLogger(__name__)

# PIL imports - optional, used for captcha generation
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = ImageDraw = ImageFont = ImageFilter = None

from .models import (
    UserInfo, ProjectInfo, TaskInfo, BudgetCost,
    DailyReminder, WeeklyPlan, QuadrantTask, WeeklySummary,
    ProjectFile, SystemSettings, TeamGroup
)


def get_or_create_user_info(username):
    """获取或创建用户信息"""
    user_info = UserInfo.objects.filter(user_name=username).first()
    if not user_info:
        user_count = UserInfo.objects.count() + 1
        user_info = UserInfo.objects.create(
            user_id=f'USER-{user_count:03d}',
            user_name=username,
            team_name='',
            contact_info=''
        )
    return user_info


def generate_captcha_image(code):
    """Generate captcha image"""
    if not PIL_AVAILABLE:
        return None
    
    try:
        width, height = 150, 50
        image = Image.new('RGB', (width, height), color=(15, 15, 25))
        draw = ImageDraw.Draw(image)
        
        # Draw background noise
        for _ in range(40):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=(random.randint(50, 80), random.randint(50, 80), random.randint(80, 120)))
        
        # Draw interference lines
        for _ in range(4):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(random.randint(60, 90), random.randint(60, 90), random.randint(100, 150)), width=1)
        
        # Draw captcha text - larger font
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        colors = ['#6366f1', '#8b5cf6', '#a855f7', '#06b6d4', '#10b981']
        for i, char in enumerate(code):
            x = 20 + i * 28
            y = random.randint(5, 10)
            color = colors[random.randint(0, len(colors) - 1)]
            draw.text((x, y), char, fill=color, font=font)
        
        return image
    except Exception:
        logger.warning("Captcha generation failed")
        return None


def captcha_view(request):
    """Generate captcha image endpoint"""
    # Generate random code
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    code = ''.join(random.choice(chars) for _ in range(4))
    
    # Store in session
    request.session['captcha_code'] = code.upper()
    request.session['captcha_time'] = datetime.now().timestamp()
    
    # Generate image
    if PIL_AVAILABLE:
        try:
            image = generate_captcha_image(code)
            if image:
                image = image.filter(ImageFilter.SMOOTH)
                buf = io.BytesIO()
                image.save(buf, 'PNG')
                buf.seek(0)
                return HttpResponse(buf.getvalue(), content_type='image/png')
        except:
            pass
    
    # Fallback: return error - captcha still works via session
    return HttpResponse(status=204)


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        captcha = request.POST.get('captcha', '').upper()
        
        # Validate captcha
        stored_captcha = request.session.get('captcha_code', '')
        captcha_time = request.session.get('captcha_time', 0)
        
        # Check captcha (valid for 5 minutes)
        if not stored_captcha or datetime.now().timestamp() - captcha_time > 300:
            messages.error(request, '验证码已过期，请刷新')
            return render(request, 'login.html')
        
        if captcha != stored_captcha:
            messages.error(request, '验证码错误')
            return render(request, 'login.html')
        
        # Validate user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Clear captcha after successful login
            request.session.pop('captcha_code', None)
            request.session.pop('captcha_time', None)
            
            # Check if UserInfo exists, create if not
            if not UserInfo.objects.filter(user_name=username).exists():
                user_count = UserInfo.objects.count() + 1
                UserInfo.objects.create(
                    user_id=f'USER-{user_count:03d}',
                    user_name=username,
                    team_name='',
                    contact_info=''
                )
            return redirect('index')
        else:
            messages.error(request, '用户名或密码错误')
    
    # Generate new captcha for GET requests (only if not exists or expired)
    captcha_time = request.session.get('captcha_time', 0)
    if not request.session.get('captcha_code') or datetime.now().timestamp() - captcha_time > 300:
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        code = ''.join(random.choice(chars) for _ in range(4))
        request.session['captcha_code'] = code.upper()
        request.session['captcha_time'] = datetime.now().timestamp()
    
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def version_upgrade(request):
    """Handle system version upgrade: upload patch and upgrade packages"""
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Forbidden")
    if not request.user.is_staff:
        return HttpResponseForbidden("Forbidden")
    # Signature check for upgrade packages (optional)
    if getattr(settings, 'VERSION_UPGRADE_SIGNATURE_ENABLED', False):
        sig = request.META.get('HTTP_X_SIGNATURE', '')
        expected = getattr(settings, 'VERSION_UPGRADE_SIGNATURE', 'OK')
        if sig != expected:
            from django.contrib import messages
            messages.error(request, '升级包签名校验失败')
            return render(request, 'settings/version_upgrade.html')
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return HttpResponseForbidden('Forbidden')
    if not request.user.is_staff:
        return HttpResponseForbidden('Forbidden')
    if request.method == 'POST':
        patch_file = request.FILES.get('patch_file')
        upgrade_file = request.FILES.get('upgrade_file')
        # determine storage dir with robust Path/String handling
        if hasattr(settings, 'VERSION_UPGRADE_DIR') and settings.VERSION_UPGRADE_DIR:
            base_dir = settings.VERSION_UPGRADE_DIR
        else:
            media_root = settings.MEDIA_ROOT
            if isinstance(media_root, str):
                base_dir = os.path.join(media_root, 'version_upgrades')
            else:
                base_dir = str(media_root / 'version_upgrades')
        os.makedirs(base_dir, exist_ok=True)
        saved = []
        if patch_file:
            patch_path = os.path.join(base_dir, f"patch_{timezone.now().strftime('%Y%m%d%H%M%S')}_{patch_file.name}")
            with open(patch_path, 'wb+') as destination:
                for chunk in patch_file.chunks():
                    destination.write(chunk)
            saved.append(patch_path)
        if upgrade_file:
            upgrade_path = os.path.join(base_dir, f"upgrade_{timezone.now().strftime('%Y%m%d%H%M%S')}_{upgrade_file.name}")
            with open(upgrade_path, 'wb+') as destination:
                for chunk in upgrade_file.chunks():
                    destination.write(chunk)
            saved.append(upgrade_path)
        from django.contrib import messages
        if saved:
            messages.success(request, '上传完成: ' + ', '.join([os.path.basename(p) for p in saved]))
            # 记录升级日志
            try:
                from .models import UpgradeLog
                user_info = get_or_create_user_info(request.user.username)
                patch_name = os.path.basename(saved[0]) if len(saved) > 0 else None
                upgrade_name = os.path.basename(saved[1]) if len(saved) > 1 else None
                UpgradeLog.objects.create(user=user_info, patch_file_name=patch_name, upgrade_file_name=upgrade_name, status='SUCCESS')
            except Exception:
                pass
        return render(request, 'settings/version_upgrade.html', {'uploaded': saved})
    return render(request, 'settings/version_upgrade.html')
    return redirect('login')


@login_required
def index(request):
    user_info = get_or_create_user_info(request.user.username)
    
    projects = ProjectInfo.objects.all()
    tasks = TaskInfo.objects.all()
    budgets = BudgetCost.objects.all()
    
    total_projects = projects.count()
    completed_projects = projects.filter(project_status='已完成').count()
    in_progress_projects = projects.filter(project_status='进行中').count()
    overdue_projects = projects.filter(project_status='逾期未完结').count()
    not_started_projects = total_projects - completed_projects - in_progress_projects - overdue_projects
    
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(task_status='已完成').count()
    in_progress_tasks = tasks.filter(task_status='进行中').count()
    overdue_tasks = tasks.filter(plan_end_date__lt=date.today(), task_status='进行中').count()
    
    total_budget = sum(b.total_budget for b in budgets)
    total_cost = sum(b.total_cost for b in budgets)
    over_budget_count = budgets.filter(remaining_budget__lt=0).count()
    
    today = date.today()
    today_reminders = DailyReminder.objects.filter(reminder_date=today, user_name=user_info)
    
    recent_projects = projects.order_by('-start_date')[:5]
    overdue_task_list = tasks.filter(plan_end_date__lt=date.today(), task_status__in=['进行中', '未开始'])[:5]
    
    context = {
        'user_info': user_info,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'in_progress_projects': in_progress_projects,
        'overdue_projects': overdue_projects,
        'not_started_projects': not_started_projects,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'total_budget': total_budget,
        'total_cost': total_cost,
        'over_budget_count': over_budget_count,
        'today_reminders': today_reminders,
        'recent_projects': recent_projects,
        'overdue_task_list': overdue_task_list,
    }
    return render(request, 'index.html', context)


@login_required
def system_monitor(request):
    # Simple system monitor using psutil if available
    cpu = mem = disk = None
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        net = psutil.net_io_counters()
        net_sent = getattr(net, 'bytes_sent', 0)
        net_recv = getattr(net, 'bytes_recv', 0)
    except Exception:
        cpu = mem = disk = None
        net_sent = net_recv = 0
    context = {
        'cpu': cpu,
        'memory': mem,
        'disk': disk,
        'net_sent': net_sent,
        'net_recv': net_recv,
    }
    return render(request, 'monitor/index.html', context)


@login_required
def dashboard_big(request):
    if request.method == 'POST':
        # Save dashboard configuration
        config_key = request.POST.get('config_key')
        config_value = request.POST.get('config_value')
        if config_key and config_value:
            SystemSettings.objects.update_or_create(
                setting_key=config_key,
                defaults={'setting_value': config_value, 'setting_type': 'dashboard'}
            )
        return JsonResponse({'status': 'success'})
    
    # Load dashboard configuration
    dashboard_config = {}
    configs = SystemSettings.objects.filter(setting_type='dashboard')
    for c in configs:
        dashboard_config[c.setting_key] = c.setting_value
    
    # Get dashboard data
    from .models import ProjectInfo, TaskInfo
    
    # Project stats
    total_projects = ProjectInfo.objects.count()
    completed_projects = ProjectInfo.objects.filter(project_status='已完成').count()
    in_progress_projects = ProjectInfo.objects.filter(project_status='进行中').count()
    
    # Task stats
    total_tasks = TaskInfo.objects.count()
    completed_tasks = TaskInfo.objects.filter(task_status='已完成').count()
    in_progress_tasks = TaskInfo.objects.filter(task_status='进行中').count()
    
    # Recent projects
    recent_projects = ProjectInfo.objects.order_by('-start_date')[:5]
    
    # Recent tasks
    recent_tasks = TaskInfo.objects.select_related('project').order_by('-plan_start_date')[:10]
    
    context = {
        'dashboard_config': dashboard_config,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'in_progress_projects': in_progress_projects,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'recent_projects': recent_projects,
        'recent_tasks': recent_tasks,
    }
    return render(request, 'dashboard_big.html', context)


@login_required
def system_reminder_counts(request):
    """Return counts for overdue tasks and today's todo items"""
    today = date.today()
    overdue = TaskInfo.objects.filter(plan_end_date__lt=today, task_status__in=['进行中','未开始']).count()
    today_todo = TaskInfo.objects.filter(plan_start_date__lte=today, plan_end_date__gte=today, task_status__in=['未开始','进行中']).count()
    return JsonResponse({'overdue': overdue, 'today_todo': today_todo})


@login_required
def logs_upgrade(request):
    """Unified logs view - combines operation logs and system logs"""
    if not request.user.is_staff:
        return HttpResponseForbidden('Forbidden')
    
    log_type = request.GET.get('type', 'all')
    all_logs = []
    
    # Get operation logs (from UpgradeLog)
    if log_type in ['all', 'operation']:
        try:
            from .models import UpgradeLog
            op_logs = UpgradeLog.objects.all().order_by('-upload_time')[:50]
            for log in op_logs:
                all_logs.append({
                    'time': log.upload_time.strftime('%Y-%m-%d %H:%M:%S') if log.upload_time else '',
                    'level': 'INFO',
                    'type': 'operation',
                    'message': f"{log.user.user_name if log.user else 'Unknown'} - {log.patch_file_name or log.upgrade_file_name or 'N/A'} ({log.status})"
                })
        except Exception:
            pass
    
    # Get system logs (sample data since no real log files)
    if log_type in ['all', 'system']:
        system_logs = [
            {'time': '2026-03-01 10:00:00', 'level': 'INFO', 'type': 'system', 'message': 'System started'},
            {'time': '2026-03-01 10:05:00', 'level': 'INFO', 'type': 'system', 'message': 'User admin logged in'},
            {'time': '2026-03-01 10:10:00', 'level': 'WARNING', 'type': 'system', 'message': 'High memory usage detected'},
            {'time': '2026-03-01 10:15:00', 'level': 'ERROR', 'type': 'system', 'message': 'Connection timeout'},
            {'time': '2026-03-01 10:20:00', 'level': 'INFO', 'type': 'system', 'message': 'Backup completed'},
        ]
        all_logs.extend(system_logs)
    
    # Sort by time descending
    all_logs.sort(key=lambda x: x['time'], reverse=True)
    
    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    page = request.GET.get('page', 1)
    paginator = Paginator(all_logs, 20)
    try:
        logs = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        logs = paginator.page(1)
    
    return render(request, 'settings/logs_upgrade.html', {
        'logs': logs,
        'log_type': log_type
    })


@login_required
def logs_system(request):
    """System logs view - displays Django system logs and application logs"""
    if not request.user.is_staff:
        return HttpResponseForbidden('Forbidden')
    
    import os
    import logging
    from pathlib import Path
    
    log_entries = []
    log_dir = Path('D:/pms')
    
    # Try to read Django log files if configured
    log_files = []
    for f in log_dir.glob('*.log'):
        log_files.append(f.name)
    for f in (log_dir / 'logs').glob('*.log') if (log_dir / 'logs').exists() else []:
        log_files.append(f'logs/{f.name}')
    
    # If no log files, show sample/placeholder data
    if not log_files:
        log_entries = [
            {'time': '2026-03-01 10:00:00', 'level': 'INFO', 'message': 'System started'},
            {'time': '2026-03-01 10:05:00', 'level': 'INFO', 'message': 'User admin logged in'},
            {'time': '2026-03-01 10:10:00', 'level': 'WARNING', 'message': 'High memory usage detected'},
            {'time': '2026-03-01 10:15:00', 'level': 'ERROR', 'message': 'Connection timeout'},
            {'time': '2026-03-01 10:20:00', 'level': 'INFO', 'message': 'Backup completed'},
        ]
    
    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    page = request.GET.get('page', 1)
    paginator = Paginator(log_entries, 20) if log_entries else Paginator(log_files, 20)
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    
    return render(request, 'settings/logs_system.html', {
        'log_entries': log_entries,
        'log_files': log_files,
        'page_obj': page_obj
    })


@login_required
def logs_upgrade_export(request):
    """Export upgrade logs as CSV"""
    if not request.user.is_staff:
        return HttpResponseForbidden('Forbidden')
    import csv
    from django.http import HttpResponse
    start = request.GET.get('start')
    end = request.GET.get('end')
    status = request.GET.get('status')
    # support dynamic column export via ?columns=col1,col2
    columns_param = request.GET.get('columns')
    if columns_param:
        columns = [c.strip() for c in columns_param.split(',') if c.strip()]
    else:
        columns = ['log_id','user','upload_time','patch_file_name','upgrade_file_name','status','notes']
    # sanitize columns to allowed set
    allowed = ['log_id','user','upload_time','patch_file_name','upgrade_file_name','status','notes']
    columns = [c for c in columns if c in allowed]

    logs = UpgradeLog.objects.all()
    if start:
        try:
            from datetime import datetime
            ds = datetime.strptime(start, '%Y-%m-%d').date()
            logs = logs.filter(upload_time__date__gte=ds)
        except Exception:
            pass
    if end:
        try:
            from datetime import datetime
            de = datetime.strptime(end, '%Y-%m-%d').date()
            logs = logs.filter(upload_time__date__lte=de)
        except Exception:
            pass
    if status:
        logs = logs.filter(status=status)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="upgrade_logs.csv"'
    writer = csv.writer(response)
    writer.writerow(columns)
    for log in logs:
        user_name = getattr(getattr(log, 'user', None), 'user_name', None)
        row = []
        for col in columns:
            if col == 'log_id':
                row.append(log.log_id)
            elif col == 'user':
                row.append(user_name or log.user)
            elif col == 'upload_time':
                row.append(log.upload_time)
            elif col == 'patch_file_name':
                row.append(log.patch_file_name)
            elif col == 'upgrade_file_name':
                row.append(log.upgrade_file_name)
            elif col == 'status':
                row.append(log.status)
            elif col == 'notes':
                row.append(log.notes)
        writer.writerow(row)
    return response


@login_required
def logs_upgrade_export_excel(request):
    if not request.user.is_staff:
        return HttpResponseForbidden('Forbidden')
    try:
        from openpyxl import Workbook
    except Exception:
        return HttpResponse('openpyxl not installed', status=501)
    try:
        from .models import UpgradeLog
        logs_qs = UpgradeLog.objects.all().order_by('-upload_time')
    except Exception:
        logs_qs = []
    # Apply same filters as CSV export
    user_id = request.GET.get('user_id')
    if user_id:
        logs_qs = logs_qs.filter(user__user_id=user_id)
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        try:
            from datetime import datetime
            ds = datetime.strptime(start, '%Y-%m-%d').date()
            logs_qs = logs_qs.filter(upload_time__date__gte=ds)
        except Exception:
            pass
    if end:
        try:
            from datetime import datetime
            de = datetime.strptime(end, '%Y-%m-%d').date()
            logs_qs = logs_qs.filter(upload_time__date__lte=de)
        except Exception:
            pass
    status = request.GET.get('status')
    if status:
        logs_qs = logs_qs.filter(status=status)

    wb = Workbook()
    ws = wb.active
    # support same columns as CSV export
    columns_param = request.GET.get('columns')
    if columns_param:
        columns = [c.strip() for c in columns_param.split(',') if c.strip()]
    else:
        columns = ['log_id','user','upload_time','patch_file_name','upgrade_file_name','status','notes']
    allowed = ['log_id','user','upload_time','patch_file_name','upgrade_file_name','status','notes']
    columns = [c for c in columns if c in allowed]
    ws.append(columns)
    for log in logs_qs:
        uname = getattr(log.user, 'user_name', None) if getattr(log, 'user', None) else None
        row = []
        for col in columns:
            if col == 'log_id':
                row.append(log.log_id)
            elif col == 'user':
                row.append(uname or log.user)
            elif col == 'upload_time':
                row.append(log.upload_time)
            elif col == 'patch_file_name':
                row.append(log.patch_file_name)
            elif col == 'upgrade_file_name':
                row.append(log.upgrade_file_name)
            elif col == 'status':
                row.append(log.status)
            elif col == 'notes':
                row.append(log.notes)
        ws.append(row)
    from django.http import HttpResponse
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="upgrade_logs.xlsx"'
    wb.save(response)
    return response

@login_required
def ui_customize(request):
    # Simple UI customization: upload login background and logo
    if request.method == 'POST':
        login_bg = request.FILES.get('login_background')
        logo_file = request.FILES.get('system_logo')
        base = settings.MEDIA_ROOT
        up_dir = os.path.join(base, 'ui')
        os.makedirs(up_dir, exist_ok=True)
        uploaded = []
        if login_bg:
            path = os.path.join(up_dir, 'login_bg' + os.path.splitext(login_bg.name)[1])
            with open(path, 'wb+') as f:
                for chunk in login_bg.chunks():
                    f.write(chunk)
            uploaded.append(path)
            SystemSettings.objects.update_or_create(
                setting_type='ui', setting_key='login_background', defaults={'setting_value': path}
            )
        if logo_file:
            path = os.path.join(up_dir, 'logo' + os.path.splitext(logo_file.name)[1])
            with open(path, 'wb+') as f:
                for chunk in logo_file.chunks():
                    f.write(chunk)
            uploaded.append(path)
            SystemSettings.objects.update_or_create(
                setting_type='ui', setting_key='system_logo', defaults={'setting_value': path}
            )
        from django.contrib import messages
        if uploaded:
            messages.success(request, '上传完成：' + ', '.join([p.split('/')[-1] for p in uploaded]))
        return render(request, 'settings/ui_customize.html', {'uploaded': uploaded})
    return render(request, 'settings/ui_customize.html')


@login_required
def project_list(request):
    user_info = get_or_create_user_info(request.user.username)
    projects = ProjectInfo.objects.all().order_by('-start_date')
    
    status_filter = request.GET.get('status')
    if status_filter:
        projects = projects.filter(project_status=status_filter)
    
    manager_filter = request.GET.get('manager')
    if manager_filter:
        projects = projects.filter(project_manager__user_name=manager_filter)
    
    context = {
        'user_info': user_info,
        'projects': projects,
        'managers': UserInfo.objects.all(),
    }
    return render(request, 'project/list.html', context)


@login_required
def project_create(request):
    user_info = get_or_create_user_info(request.user.username)
    
    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        project_manager_id = request.POST.get('project_manager')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        key_content_count = int(request.POST.get('key_content_count', 0))
        remark = request.POST.get('remark', '')
        
        project_manager = get_object_or_404(UserInfo, user_id=project_manager_id)
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        year = datetime.now().year
        count = ProjectInfo.objects.filter(project_id__startswith=f'PROJECT-{year}').count() + 1
        project_id = f'PROJECT-{year}-{count:03d}'
        
        project = ProjectInfo.objects.create(
            project_id=project_id,
            project_name=project_name,
            project_manager=project_manager,
            start_date=start_date,
            end_date=end_date,
            key_content_count=key_content_count,
            remark=remark,
            project_status='未开始'
        )
        
        messages.success(request, f'项目 {project_name} 创建成功')
        return redirect('project_list')
    
    context = {
        'user_info': user_info,
        'managers': UserInfo.objects.all(),
    }
    return render(request, 'project/create.html', context)


@login_required
def project_edit(request, project_id):
    user_info = get_or_create_user_info(request.user.username)
    project = get_object_or_404(ProjectInfo, project_id=project_id)
    
    if request.method == 'POST':
        project.project_name = request.POST.get('project_name')
        project_manager_id = request.POST.get('project_manager')
        project.project_manager = get_object_or_404(UserInfo, user_id=project_manager_id)
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        project.key_content_count = int(request.POST.get('key_content_count', 0))
        project.remark = request.POST.get('remark', '')
        project.save()
        
        messages.success(request, f'项目 {project.project_name} 更新成功')
        return redirect('project_list')
    
    context = {
        'user_info': user_info,
        'project': project,
        'managers': UserInfo.objects.all(),
    }
    return render(request, 'project/edit.html', context)


@login_required
def project_delete(request, project_id):
    project = get_object_or_404(ProjectInfo, project_id=project_id)
    project.delete()
    messages.success(request, '项目删除成功')
    return redirect('project_list')


@login_required
def gantt_view(request):
    user_info = get_or_create_user_info(request.user.username)
    view_type = request.GET.get('view', 'project')
    projects = ProjectInfo.objects.all().order_by('start_date')
    
    gantt_data = []
    for project in projects:
        tasks = project.tasks.all()
        gantt_data.append({
            'project': project,
            'tasks': tasks
        })
    
    # Get all tasks for task view
    all_tasks = TaskInfo.objects.all().select_related('project', 'task_owner').order_by('plan_start_date')
    
    # Calculate dynamic date range based on projects (daily timeline)
    if projects:
        min_date = min(p.start_date for p in projects if p.start_date) if any(p.start_date for p in projects) else date.today()
        max_date = max(p.end_date for p in projects if p.end_date) if any(p.end_date for p in projects) else date.today() + timedelta(days=30)
    else:
        min_date = date.today()
        max_date = date.today() + timedelta(days=30)
    
    # Build days range
    days = []
    cur = min_date
    while cur <= max_date:
        days.append(cur.day)
        cur += timedelta(days=1)
    
    context = {
        'user_info': user_info,
        'gantt_data': gantt_data,
        'all_tasks': all_tasks,
        'gantt_days': days,
        'gantt_start_date': min_date,
        'view_type': view_type,
    }
    return render(request, 'project/gantt.html', context)


@login_required
def task_list(request):
    user_info = get_or_create_user_info(request.user.username)
    tasks = TaskInfo.objects.all().select_related('project', 'task_owner').order_by('-plan_start_date')
    
    project_filter = request.GET.get('project')
    if project_filter:
        tasks = tasks.filter(project__project_id=project_filter)
    
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(task_status=status_filter)
    
    owner_filter = request.GET.get('owner')
    if owner_filter:
        tasks = tasks.filter(task_owner__user_name=owner_filter)
    
    context = {
        'user_info': user_info,
        'tasks': tasks,
        'projects': ProjectInfo.objects.all(),
        'owners': UserInfo.objects.all(),
    }
    return render(request, 'task/list.html', context)


@login_required
def task_create(request):
    user_info = get_or_create_user_info(request.user.username)
    
    if request.method == 'POST':
        project_id = request.POST.get('project')
        key_content_name = request.POST.get('key_content_name')
        priority_level = request.POST.get('priority_level')
        task_owner_id = request.POST.get('task_owner')
        plan_start_date = request.POST.get('plan_start_date')
        plan_end_date = request.POST.get('plan_end_date')
        
        project = get_object_or_404(ProjectInfo, project_id=project_id)
        task_owner = get_object_or_404(UserInfo, user_id=task_owner_id)
        
        task_count = TaskInfo.objects.filter(project=project).count() + 1
        task_id = f'TASK-{project_id}-{task_count:03d}'
        
        task = TaskInfo.objects.create(
            task_id=task_id,
            project=project,
            key_content_name=key_content_name,
            priority_level=priority_level,
            task_owner=task_owner,
            plan_start_date=plan_start_date,
            plan_end_date=plan_end_date,
            task_status='未开始'
        )
        
        project.not_started_count += 1
        project.save()
        
        messages.success(request, f'任务 {key_content_name} 创建成功')
        return redirect('task_list')
    
    context = {
        'user_info': user_info,
        'projects': ProjectInfo.objects.all(),
        'owners': UserInfo.objects.all(),
    }
    return render(request, 'task/create.html', context)


@login_required
def task_edit(request, task_id):
    user_info = get_or_create_user_info(request.user.username)
    task = get_object_or_404(TaskInfo, task_id=task_id)
    
    if request.method == 'POST':
        task.key_content_name = request.POST.get('key_content_name')
        task.priority_level = request.POST.get('priority_level')
        task_owner_id = request.POST.get('task_owner')
        task.task_owner = get_object_or_404(UserInfo, user_id=task_owner_id)
        task.plan_start_date = request.POST.get('plan_start_date')
        task.plan_end_date = request.POST.get('plan_end_date')
        task.completion_remark = request.POST.get('completion_remark', '')
        
        new_status = request.POST.get('task_status')
        if new_status and new_status != task.task_status:
            old_status = task.task_status
            task.task_status = new_status
            
            project = task.project
            if old_status == '未开始':
                project.not_started_count -= 1
            elif old_status == '进行中':
                project.in_progress_count -= 1
            elif old_status == '已完成':
                project.completed_count -= 1
            
            if new_status == '未开始':
                project.not_started_count += 1
            elif new_status == '进行中':
                project.in_progress_count += 1
            elif new_status == '已完成':
                project.completed_count += 1
                task.actual_complete_date = date.today()
            
            project.save()
        
        task.save()
        messages.success(request, f'任务 {task.key_content_name} 更新成功')
        return redirect('task_list')
    
    context = {
        'user_info': user_info,
        'task': task,
        'projects': ProjectInfo.objects.all(),
        'owners': UserInfo.objects.all(),
    }
    return render(request, 'task/edit.html', context)


@login_required
def task_delete(request, task_id):
    task = get_object_or_404(TaskInfo, task_id=task_id)
    project = task.project
    
    if task.task_status == '未开始':
        project.not_started_count -= 1
    elif task.task_status == '进行中':
        project.in_progress_count -= 1
    elif task.task_status == '已完成':
        project.completed_count -= 1
    
    project.save()
    task.delete()
    messages.success(request, '任务删除成功')
    return redirect('task_list')


@login_required
def budget_list(request):
    user_info = get_or_create_user_info(request.user.username)
    budgets = BudgetCost.objects.all().order_by('-project__start_date')
    
    context = {
        'user_info': user_info,
        'budgets': budgets,
    }
    return render(request, 'budget/list.html', context)


@login_required
def budget_create(request):
    user_info = get_or_create_user_info(request.user.username)
    
    if request.method == 'POST':
        project_id = request.POST.get('project')
        project = get_object_or_404(ProjectInfo, project_id=project_id)
        
        budget_count = BudgetCost.objects.count() + 1
        budget_id = f'BUDGET-{project_id}-{budget_count:03d}'
        
        workday_count = int(request.POST.get('workday_count', 0))
        participant_count = int(request.POST.get('participant_count', 0))
        
        budget = BudgetCost.objects.create(
            budget_id=budget_id,
            project=project,
            project_name=project.project_name,
            project_manager=project.project_manager.user_name,
            start_date=project.start_date,
            end_date=project.end_date,
            workday_count=workday_count,
            participant_count=participant_count,
            total_budget=Decimal(request.POST.get('total_budget', 0)),
            personnel_cost=Decimal(request.POST.get('personnel_cost', 0)),
            rnd_cost=Decimal(request.POST.get('rnd_cost', 0)),
            design_cost=Decimal(request.POST.get('design_cost', 0)),
            travel_cost=Decimal(request.POST.get('travel_cost', 0)),
            marketing_cost=Decimal(request.POST.get('marketing_cost', 0)),
        )
        
        messages.success(request, f'项目预算创建成功')
        return redirect('budget_list')
    
    context = {
        'user_info': user_info,
        'projects': ProjectInfo.objects.all(),
    }
    return render(request, 'budget/create.html', context)


@login_required
def budget_edit(request, budget_id):
    user_info = get_or_create_user_info(request.user.username)
    budget = get_object_or_404(BudgetCost, budget_id=budget_id)
    
    if request.method == 'POST':
        budget.workday_count = int(request.POST.get('workday_count', 0))
        budget.participant_count = int(request.POST.get('participant_count', 0))
        budget.total_budget = Decimal(request.POST.get('total_budget', 0))
        budget.personnel_cost = Decimal(request.POST.get('personnel_cost', 0))
        budget.rnd_cost = Decimal(request.POST.get('rnd_cost', 0))
        budget.design_cost = Decimal(request.POST.get('design_cost', 0))
        budget.travel_cost = Decimal(request.POST.get('travel_cost', 0))
        budget.marketing_cost = Decimal(request.POST.get('marketing_cost', 0))
        budget.cost_remark = request.POST.get('cost_remark', '')
        budget.save()
        
        messages.success(request, '预算更新成功')
        return redirect('budget_list')
    
    context = {
        'user_info': user_info,
        'budget': budget,
    }
    return render(request, 'budget/edit.html', context)


@login_required
def user_list(request):
    user_info = get_or_create_user_info(request.user.username)
    teams = TeamGroup.objects.all()
    
    for team in teams:
        team.member_count = team.members.count()
    
    context = {
        'user_info': user_info,
        'teams': teams,
        'all_users': UserInfo.objects.all(),
    }
    return render(request, 'user/list.html', context)


@login_required
def team_create(request):
    user_info = get_or_create_user_info(request.user.username)
    
    if request.method == 'POST':
        team_name = request.POST.get('team_name')
        member_ids = request.POST.getlist('members')
        remark = request.POST.get('remark', '')
        
        team_count = TeamGroup.objects.count() + 1
        team_id = f'TEAM-{team_count:03d}'
        
        team = TeamGroup.objects.create(
            team_id=team_id,
            team_name=team_name,
            remark=remark
        )
        
        for member_id in member_ids:
            member = UserInfo.objects.filter(user_id=member_id).first()
            if member:
                team.members.add(member)
        
        messages.success(request, f'团队 {team_name} 创建成功')
        return redirect('user_list')
    
    context = {
        'user_info': user_info,
        'users': UserInfo.objects.all(),
    }
    return render(request, 'user/team_create.html', context)


@login_required
def team_edit(request, team_id):
    user_info = get_or_create_user_info(request.user.username)
    team = get_object_or_404(TeamGroup, team_id=team_id)
    
    if request.method == 'POST':
        team.team_name = request.POST.get('team_name')
        team.remark = request.POST.get('remark', '')
        team.members.clear()
        
        member_ids = request.POST.getlist('members')
        for member_id in member_ids:
            member = UserInfo.objects.filter(user_id=member_id).first()
            if member:
                team.members.add(member)
        
        team.save()
        messages.success(request, f'团队 {team.team_name} 更新成功')
        return redirect('user_list')
    
    context = {
        'user_info': user_info,
        'team': team,
        'users': UserInfo.objects.all(),
    }
    return render(request, 'user/team_edit.html', context)


@login_required
def team_delete(request, team_id):
    team = get_object_or_404(TeamGroup, team_id=team_id)
    team_name = team.team_name
    team.delete()
    messages.success(request, f'团队 {team_name} 删除成功')
    return redirect('user_list')


@login_required
def user_create(request):
    user_info = get_or_create_user_info(request.user.username)
    
    if request.method == 'POST':
        user_count = UserInfo.objects.count() + 1
        user_id = f'USER-{user_count:03d}'
        
        user = UserInfo.objects.create(
            user_id=user_id,
            user_name=request.POST.get('user_name'),
            team_name=request.POST.get('team_name', ''),
            contact_info=request.POST.get('contact_info', ''),
        )
        
        messages.success(request, f'用户 {user.user_name} 创建成功')
        return redirect('user_list')
    
    context = {
        'user_info': user_info,
    }
    return render(request, 'user/create.html', context)


@login_required
def user_edit(request, user_id):
    user_info = get_or_create_user_info(request.user.username)
    user = get_object_or_404(UserInfo, user_id=user_id)
    
    if request.method == 'POST':
        user.user_name = request.POST.get('user_name')
        user.team_name = request.POST.get('team_name', '')
        user.contact_info = request.POST.get('contact_info', '')
        user.save()
        
        messages.success(request, f'用户 {user.user_name} 更新成功')
        return redirect('user_list')
    
    context = {
        'user_info': user_info,
        'user': user,
    }
    return render(request, 'user/edit.html', context)


@login_required
def user_delete(request, user_id):
    user = get_object_or_404(UserInfo, user_id=user_id)
    user.delete()
    messages.success(request, '用户删除成功')
    return redirect('user_list')


@login_required
def reminder_list(request):
    user_info = get_or_create_user_info(request.user.username)
    
    reminder_date = request.GET.get('date')
    today_date = date.today()
    if reminder_date:
        reminders = DailyReminder.objects.filter(reminder_date=reminder_date, user_name=user_info)
    else:
        reminders = DailyReminder.objects.filter(reminder_date=today_date, user_name=user_info)
    
    context = {
        'user_info': user_info,
        'reminders': reminders,
        'today': today_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'reminder/list.html', context)


@login_required
def weekly_plan_list(request):
    user_info = get_or_create_user_info(request.user.username)
    
    week = request.GET.get('week')
    if week:
        plans = WeeklyPlan.objects.filter(plan_week=week, user_name=user_info)
    else:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_str = f'{week_start.strftime("%Y-%m-%d")} 至 {week_end.strftime("%Y-%m-%d")}'
        plans = WeeklyPlan.objects.filter(user_name=user_info, plan_week=week_str)
    
    context = {
        'user_info': user_info,
        'plans': plans,
    }
    return render(request, 'weekly/plan_list.html', context)


@login_required
def weekly_plan_create(request):
    user_info = get_or_create_user_info(request.user.username)
    
    # If today is weekend, disallow creating a weekly plan
    if date.today().weekday() >= 5:
        messages.error(request, '周计划仅允许工作日创建。')
        return redirect('weekly_plan_list')
    
    if request.method == 'POST':
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        plan_week = f'{week_start.strftime("%Y-%m-%d")} 至 {week_end.strftime("%Y-%m-%d")}'
        
        year = today.year
        week_num = today.isocalendar()[1]
        plan_id = f'WEEKLY-{year}-{week_num}-{UserInfo.objects.count() + 1:03d}'
        
        plan = WeeklyPlan.objects.create(
            plan_id=plan_id,
            user_name=user_info,
            plan_week=plan_week,
            monday_task=request.POST.get('monday_task', ''),
            tuesday_task=request.POST.get('tuesday_task', ''),
            wednesday_task=request.POST.get('wednesday_task', ''),
            thursday_task=request.POST.get('thursday_task', ''),
            friday_task=request.POST.get('friday_task', ''),
            saturday_task=request.POST.get('saturday_task', ''),
            sunday_task=request.POST.get('sunday_task', ''),
        )
        
        messages.success(request, '周计划创建成功')
        return redirect('weekly_plan_list')
    
    context = {
        'user_info': user_info,
    }
    return render(request, 'weekly/plan_create.html', context)


@login_required
def weekly_plan_edit(request, plan_id):
    user_info = get_or_create_user_info(request.user.username)
    plan = get_object_or_404(WeeklyPlan, plan_id=plan_id, user_name=user_info)
    
    if request.method == 'POST':
        plan.monday_task = request.POST.get('monday_task', '')
        plan.tuesday_task = request.POST.get('tuesday_task', '')
        plan.wednesday_task = request.POST.get('wednesday_task', '')
        plan.thursday_task = request.POST.get('thursday_task', '')
        plan.friday_task = request.POST.get('friday_task', '')
        plan.saturday_task = request.POST.get('saturday_task', '')
        plan.sunday_task = request.POST.get('sunday_task', '')
        plan.save()
        
        messages.success(request, '周计划更新成功')
        return redirect('weekly_plan_list')
    
    context = {
        'user_info': user_info,
        'plan': plan,
    }
    return render(request, 'weekly/plan_edit.html', context)


@login_required
def weekly_plan_delete(request, plan_id):
    user_info = get_or_create_user_info(request.user.username)
    plan = get_object_or_404(WeeklyPlan, plan_id=plan_id, user_name=user_info)
    plan.delete()
    messages.success(request, '周计划删除成功')
    return redirect('weekly_plan_list')


@login_required
def quadrant_list(request):
    user_info = get_or_create_user_info(request.user.username)
    
    stat_cycle = request.GET.get('cycle', '本月')
    quadrant_type = request.GET.get('quadrant')
    
    tasks = QuadrantTask.objects.filter(user_name=user_info)
    
    if stat_cycle:
        tasks = tasks.filter(stat_cycle=stat_cycle)
    if quadrant_type:
        tasks = tasks.filter(quadrant_type=quadrant_type)
    
    context = {
        'user_info': user_info,
        'urgent_important': tasks.filter(quadrant_type='优先级1-重要紧急'),
        'important_not_urgent': tasks.filter(quadrant_type='优先级2-重要不紧急'),
        'urgent_not_important': tasks.filter(quadrant_type='优先级3-紧急不重要'),
        'not_urgent_not_important': tasks.filter(quadrant_type='优先级4-不紧急不重要'),
        'stat_cycle': stat_cycle,
    }
    return render(request, 'quadrant/list.html', context)


@login_required
def summary_list(request):
    user_info = get_or_create_user_info(request.user.username)
    
    summaries = WeeklySummary.objects.filter(user_name=user_info).order_by('-summary_week')
    
    context = {
        'user_info': user_info,
        'summaries': summaries,
    }
    return render(request, 'summary/list.html', context)


@login_required
def summary_create(request):
    user_info = get_or_create_user_info(request.user.username)
    
    if request.method == 'POST':
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        summary_week = f'{week_start.strftime("%Y-%m-%d")} 至 {week_end.strftime("%Y-%m-%d")}'
        
        year = today.year
        week_num = today.isocalendar()[1]
        summary_id = f'SUMMARY-{year}-{week_num}-{UserInfo.objects.count() + 1:03d}'
        
        summary = WeeklySummary.objects.create(
            summary_id=summary_id,
            user_name=user_info,
            summary_week=summary_week,
            completed_work=request.POST.get('completed_work', ''),
            uncompleted_work=request.POST.get('uncompleted_work', ''),
            next_week_plan=request.POST.get('next_week_plan', ''),
            problems_suggestions=request.POST.get('problems_suggestions', ''),
        )
        
        messages.success(request, '周总结创建成功')
        return redirect('summary_list')
    
    context = {
        'user_info': user_info,
    }
    return render(request, 'summary/create.html', context)


@login_required
def api_get_tasks_by_project(request, project_id):
    project = get_object_or_404(ProjectInfo, project_id=project_id)
    tasks = project.tasks.all()
    
    data = []
    for task in tasks:
        data.append({
            'task_id': task.task_id,
            'key_content_name': task.key_content_name,
            'priority_level': task.priority_level,
            'task_owner': task.task_owner.user_name,
            'plan_start_date': task.plan_start_date.strftime('%Y-%m-%d'),
            'plan_end_date': task.plan_end_date.strftime('%Y-%m-%d'),
            'task_status': task.task_status,
        })
    
    return JsonResponse({'tasks': data})


@login_required
def api_sync_reminders(request):
    today = date.today()
    
    DailyReminder.objects.filter(reminder_date=today).delete()
    
    tasks = TaskInfo.objects.filter(task_status__in=['进行中', '未开始'])
    
    for task in tasks:
        days_until_end = (task.plan_end_date - today).days
        overdue_days = 0
        
        if days_until_end < 0:
            task_type = '已逾期'
            overdue_days = abs(days_until_end)
        elif days_until_end == 0:
            task_type = '今日截止'
            overdue_days = 0
        elif (task.plan_end_date - today).days <= 7:
            task_type = '周期内未完成'
            overdue_days = 0
        else:
            task_type = '今日开始' if task.plan_start_date == today else None
        
        if task_type:
            reminder_count = DailyReminder.objects.count() + 1
            reminder_id = f'REMINDER-{today.strftime("%Y%m%d")}-{reminder_count:03d}'
            
            DailyReminder.objects.create(
                reminder_id=reminder_id,
                reminder_date=today,
                user_name=task.task_owner,
                project=task.project,
                project_name=task.project.project_name,
                key_content_name=task.key_content_name,
                task_type=task_type,
                task_status=task.task_status,
                overdue_days=overdue_days if task_type == '已逾期' else 0,
            )
    
    return JsonResponse({'status': 'success', 'message': f'已同步{len(tasks)}条提醒'})


@login_required
def api_sync_quadrants(request):
    QuadrantTask.objects.all().delete()
    
    tasks = TaskInfo.objects.filter(task_status__in=['进行中', '未开始'])
    
    quadrant_map = {
        '优先级1': '优先级1-重要紧急',
        '优先级2': '优先级2-重要不紧急',
        '优先级3': '优先级3-紧急不重要',
        '优先级4': '优先级4-不紧急不重要',
    }
    
    for task in tasks:
        quadrant_type = quadrant_map.get(task.priority_level, '优先级4-不紧急不重要')
        
        quadrant_count = QuadrantTask.objects.count() + 1
        quadrant_id = f'QUADRANT-{date.today().strftime("%Y%m%d")}-{quadrant_count:03d}'
        
        QuadrantTask.objects.create(
            quadrant_id=quadrant_id,
            user_name=task.task_owner,
            stat_cycle='本月',
            quadrant_type=quadrant_type,
            project=task.project,
            project_name=task.project.project_name,
            key_content_name=task.key_content_name,
            task_owner=task.task_owner,
            end_date=task.plan_end_date,
            task_status=task.task_status,
        )
    
    return JsonResponse({'status': 'success', 'message': f'已同步{len(tasks)}条四象限任务'})


@login_required
def api_update_project_progress(request, project_id):
    project = get_object_or_404(ProjectInfo, project_id=project_id)
    
    project.completed_count = project.tasks.filter(task_status='已完成').count()
    project.in_progress_count = project.tasks.filter(task_status='进行中').count()
    project.not_started_count = project.tasks.filter(task_status='未开始').count()
    
    if project.key_content_count > 0:
        project.completion_progress = round((project.completed_count / project.key_content_count) * 100, 2)
    
    if project.completed_count == project.key_content_count and project.key_content_count > 0:
        project.project_status = '已完成'
    elif project.completed_count > 0 or project.in_progress_count > 0:
        if date.today() > project.end_date:
            project.project_status = '逾期未完结'
        else:
            project.project_status = '进行中'
    else:
        project.project_status = '未开始'
    
    project.save()
    
    return JsonResponse({'status': 'success', 'project_status': project.project_status})


@login_required
def settings_view(request):
    user_info = get_or_create_user_info(request.user.username)
    context = {
        'user_info': user_info,
    }
    return render(request, 'settings/index.html', context)


@login_required
def settings_profile(request):
    user_info = get_or_create_user_info(request.user.username)
    
    if request.method == 'POST':
        user_info.user_name = request.POST.get('user_name', user_info.user_name)
        user_info.team_name = request.POST.get('team_name', '')
        user_info.contact_info = request.POST.get('contact_info', '')
        user_info.save()
        messages.success(request, '个人信息更新成功')
        return redirect('settings')
    
    context = {
        'user_info': user_info,
    }
    return render(request, 'settings/profile.html', context)


@login_required
def settings_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        
        if not user.check_password(old_password):
            messages.error(request, '原密码错误')
            return redirect('settings_password')
        
        if new_password != confirm_password:
            messages.error(request, '两次输入的新密码不一致')
            return redirect('settings_password')
        
        if len(new_password) < 8:
            messages.error(request, '新密码长度至少8位')
            return redirect('settings_password')
        
        user.set_password(new_password)
        user.save()
        
        messages.success(request, '密码修改成功，请重新登录')
        from django.contrib.auth import logout
        logout(request)
        return redirect('login')
    
    context = {
        'user_info': get_or_create_user_info(request.user.username),
    }
    return render(request, 'settings/password.html', context)


@login_required
def settings_ai(request):
    """AI配置设置"""
    user_info = get_or_create_user_info(request.user.username)
    
    ai_settings = SystemSettings.objects.filter(setting_type='ai')
    ai_config = {s.setting_key: s for s in ai_settings}
    
    if request.method == 'POST':
        ai_url = request.POST.get('ai_url', '').strip()
        ai_key = request.POST.get('ai_key', '').strip()
        
        SystemSettings.objects.update_or_create(
            setting_type='ai',
            setting_key='ai_url',
            defaults={'setting_value': ai_url, 'is_enabled': bool(ai_url), 'description': 'AI服务URL'}
        )
        SystemSettings.objects.update_or_create(
            setting_type='ai',
            setting_key='ai_key',
            defaults={'setting_value': ai_key, 'is_enabled': bool(ai_key), 'description': 'AI服务密钥'}
        )
        
        messages.success(request, 'AI配置保存成功')
        return redirect('settings_ai')
    
    context = {
        'user_info': user_info,
        'ai_url': ai_config.get('ai_url', {}).setting_value if 'ai_url' in ai_config else '',
        'ai_key': ai_config.get('ai_key', {}).setting_value if 'ai_key' in ai_config else '',
    }
    return render(request, 'settings/ai.html', context)


@login_required
def settings_email(request):
    """邮件配置设置"""
    user_info = get_or_create_user_info(request.user.username)
    
    email_settings = SystemSettings.objects.filter(setting_type='email')
    email_config = {s.setting_key: s for s in email_settings}
    
    if request.method == 'POST':
        email_host = request.POST.get('email_host', '').strip()
        email_port = request.POST.get('email_port', '').strip()
        email_user = request.POST.get('email_user', '').strip()
        email_password = request.POST.get('email_password', '').strip()
        email_from = request.POST.get('email_from', '').strip()
        enable_email_notify = request.POST.get('enable_email_notify') == 'on'
        
        for key, value in [
            ('email_host', email_host),
            ('email_port', email_port),
            ('email_user', email_user),
            ('email_password', email_password),
            ('email_from', email_from),
        ]:
            SystemSettings.objects.update_or_create(
                setting_type='email',
                setting_key=key,
                defaults={'setting_value': value, 'description': f'邮件{key}'}
            )
        
        SystemSettings.objects.update_or_create(
            setting_type='email',
            setting_key='enable_notify',
            defaults={'setting_value': str(enable_email_notify), 'is_enabled': enable_email_notify, 'description': '启用邮件通知'}
        )
        
        messages.success(request, '邮件配置保存成功')
        return redirect('settings_email')
    
    context = {
        'user_info': user_info,
        'email_host': email_config.get('email_host', {}).setting_value if 'email_host' in email_config else '',
        'email_port': email_config.get('email_port', {}).setting_value if 'email_port' in email_config else '587',
        'email_user': email_config.get('email_user', {}).setting_value if 'email_user' in email_config else '',
        'email_password': email_config.get('email_password', {}).setting_value if 'email_password' in email_config else '',
        'email_from': email_config.get('email_from', {}).setting_value if 'email_from' in email_config else '',
        'enable_notify': email_config.get('enable_notify', {}).is_enabled if 'enable_notify' in email_config else False,
    }
    return render(request, 'settings/email.html', context)


@login_required
def settings_security(request):
    """安全设置"""
    user_info = get_or_create_user_info(request.user.username)
    
    security_settings = SystemSettings.objects.filter(setting_type='security')
    security_config = {s.setting_key: s for s in security_settings}
    
    if request.method == 'POST':
        enable_captcha = request.POST.get('enable_captcha') == 'on'
        enable_2fa = request.POST.get('enable_2fa') == 'on'
        session_timeout = request.POST.get('session_timeout', '30')
        
        for key, value, desc in [
            ('enable_captcha', str(enable_captcha), '启用验证码'),
            ('enable_2fa', str(enable_2fa), '启用双因素认证'),
            ('session_timeout', session_timeout, '会话超时时间(分钟)'),
        ]:
            SystemSettings.objects.update_or_create(
                setting_type='security',
                setting_key=key,
                defaults={'setting_value': value, 'is_enabled': value == 'True', 'description': desc}
            )
        
        messages.success(request, '安全设置保存成功')
        return redirect('settings_security')
    
    context = {
        'user_info': user_info,
        'enable_captcha': security_config.get('enable_captcha', {}).is_enabled if 'enable_captcha' in security_config else False,
        'enable_2fa': security_config.get('enable_2fa', {}).is_enabled if 'enable_2fa' in security_config else False,
        'session_timeout': security_config.get('session_timeout', {}).setting_value if 'session_timeout' in security_config else '30',
    }
    return render(request, 'settings/security.html', context)


@login_required
def ai_generate_summary(request):
    """AI生成周总结"""
    if request.method == 'POST':
        import json
        try:
            ai_config = SystemSettings.objects.filter(setting_type='ai')
            ai_url = ai_config.filter(setting_key='ai_url').first()
            ai_key = ai_config.filter(setting_key='ai_key').first()
            
            ai_url = ai_url.setting_value if ai_url else ''
            ai_key = ai_key.setting_value if ai_key else ''
            
            if not ai_url or not ai_key:
                return JsonResponse({'success': False, 'error': '请先配置AI服务'})
            
            week_str = request.POST.get('week', '')
            user_info = get_or_create_user_info(request.user.username)
            
            plans = WeeklyPlan.objects.filter(user_name=user_info, plan_week=week_str)
            if not plans.exists():
                return JsonResponse({'success': False, 'error': '未找到该周计划'})
            
            plan = plans.first()
            tasks_text = f"""
周一: {plan.monday_task or '无'}
周二: {plan.tuesday_task or '无'}
周三: {plan.wednesday_task or '无'}
周四: {plan.thursday_task or '无'}
周五: {plan.friday_task or '无'}
周六: {plan.saturday_task or '无'}
周日: {plan.sunday_task or '无'}
已完成: {plan.completed_count or 0}
进行中: {plan.in_progress_count or 0}
未开始: {plan.not_started_count or 0}
"""
            
            prompt = f"""请根据以下周计划任务内容，生成一份本周工作总结：
{tasks_text}

请用中文总结，包括：
1. 本周完成的主要工作
2. 遇到的问题和解决方案
3. 下周工作计划
格式要清晰规范"""

            import requests
            headers = {
                'Authorization': f'Bearer {ai_key}',
                'Content-Type': 'application/json'
            }
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7
            }
            
            response = requests.post(ai_url, headers=headers, json=data, timeout=30)
            result = response.json()
            
            summary_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            return JsonResponse({'success': True, 'summary': summary_text})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def monitor_view(request):
    """项目实时监控大屏"""
    user_info = get_or_create_user_info(request.user.username)
    
    projects = ProjectInfo.objects.all()
    tasks = TaskInfo.objects.all()
    budgets = BudgetCost.objects.all()
    
    # 项目统计
    total_projects = projects.count()
    completed_projects = projects.filter(project_status='已完成').count()
    in_progress_projects = projects.filter(project_status='进行中').count()
    overdue_projects = projects.filter(project_status='逾期未完结').count()
    not_started_projects = total_projects - completed_projects - in_progress_projects - overdue_projects
    
    # 任务统计
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(task_status='已完成').count()
    in_progress_tasks = tasks.filter(task_status='进行中').count()
    overdue_tasks = tasks.filter(plan_end_date__lt=date.today(), task_status='进行中').count()
    
    # 预算统计
    total_budget = sum(b.total_budget for b in budgets)
    total_cost = sum(b.total_cost for b in budgets)
    over_budget_count = budgets.filter(remaining_budget__lt=0).count()
    
    # 最近项目
    recent_projects = projects.order_by('-start_date')[:5]
    
    # 逾期任务
    overdue_task_list = tasks.filter(plan_end_date__lt=date.today(), task_status__in=['进行中', '未开始'])[:10]
    
    context = {
        'user_info': user_info,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'in_progress_projects': in_progress_projects,
        'overdue_projects': overdue_projects,
        'not_started_projects': not_started_projects,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'total_budget': total_budget,
        'total_cost': total_cost,
        'over_budget_count': over_budget_count,
        'recent_projects': recent_projects,
        'overdue_task_list': overdue_task_list,
    }
    return render(request, 'monitor/index.html', context)


@login_required
def api_monitor_data(request):
    """获取监控数据API"""
    projects = ProjectInfo.objects.all()
    tasks = TaskInfo.objects.all()
    budgets = BudgetCost.objects.all()
    
    # 项目状态分布
    project_status = {
        '已完成': projects.filter(project_status='已完成').count(),
        '进行中': projects.filter(project_status='进行中').count(),
        '未开始': projects.filter(project_status='未开始').count(),
        '逾期未完结': projects.filter(project_status='逾期未完结').count(),
    }
    
    # 任务状态分布
    task_status = {
        '已完成': tasks.filter(task_status='已完成').count(),
        '进行中': tasks.filter(task_status='进行中').count(),
        '未开始': tasks.filter(task_status='未开始').count(),
    }
    
    # 预算使用情况
    budget_data = []
    for budget in budgets[:10]:
        budget_data.append({
            'name': budget.project_name[:10],
            'budget': float(budget.total_budget),
            'used': float(budget.total_cost),
            'remaining': float(budget.remaining_budget),
        })
    
    return JsonResponse({
        'project_status': project_status,
        'task_status': task_status,
        'budget_data': budget_data,
        'cpu': get_cpu(),
        'memory': get_memory(),
        'disk': get_disk(),
        'net_sent': get_net_sent(),
        'net_recv': get_net_recv(),
    })


def get_cpu():
    try:
        import psutil
        return psutil.cpu_percent(interval=0.1)
    except:
        return 0

def get_memory():
    try:
        import psutil
        return psutil.virtual_memory().percent
    except:
        return 0

def get_disk():
    try:
        import psutil
        return psutil.disk_usage('/').percent
    except:
        return 0

def get_net_sent():
    try:
        import psutil
        return psutil.net_io_counters().bytes_sent
    except:
        return 0

def get_net_recv():
    try:
        import psutil
        return psutil.net_io_counters().bytes_recv
    except:
        return 0


# ==================== 文件管理 ====================
import os
from django.conf import settings

@login_required
def file_list(request):
    """文件列表"""
    user_info = get_or_create_user_info(request.user.username)
    
    files = ProjectFile.objects.all().order_by('-upload_date')
    
    context = {
        'user_info': user_info,
        'files': files,
    }
    return render(request, 'files/list.html', context)


@login_required
def file_upload(request):
    """文件上传"""
    user_info = get_or_create_user_info(request.user.username)
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        description = request.POST.get('description', '')
        
        if uploaded_file:
            # 文件安全验证
            import re
            ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
            
            # 验证文件扩展名
            ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
            if not ext or ext not in ALLOWED_EXTENSIONS:
                messages.error(request, '不支持的文件类型')
                return redirect('file_upload')
            
            # 验证文件大小
            if uploaded_file.size > MAX_FILE_SIZE:
                messages.error(request, '文件大小不能超过10MB')
                return redirect('file_upload')
            
            # 清理文件名，防止路径遍历
            safe_filename = re.sub(r'[^\w\s.-]', '', uploaded_file.name)
            safe_filename = safe_filename[:100]  # 限制长度
            
            # 创建上传目录
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # 保存文件
            import uuid
            safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
            file_path = os.path.join(upload_dir, safe_filename)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # 保存记录
            ProjectFile.objects.create(
                file_name=safe_filename,
                file_path=f'uploads/{safe_filename}',
                file_size=uploaded_file.size,
                description=description[:200],
                uploaded_by=user_info,
            )
            
            messages.success(request, f'文件上传成功')
        
        return redirect('file_list')
    
    context = {
        'user_info': user_info,
    }
    return render(request, 'files/upload.html', context)


@login_required
def file_delete(request, file_id):
    """删除文件"""
    file = get_object_or_404(ProjectFile, id=file_id)
    
    # 删除物理文件
    full_path = os.path.join(settings.MEDIA_ROOT, file.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    
    # 删除记录
    file.delete()
    messages.success(request, '文件删除成功')
    
    return redirect('file_list')


@login_required
def file_download(request, file_id):
    """下载文件"""
    from django.http import FileResponse
    
    file = get_object_or_404(ProjectFile, id=file_id)
    full_path = os.path.join(settings.MEDIA_ROOT, file.file_path)
    
    return FileResponse(open(full_path, 'rb'), as_attachment=True, filename=file.file_name)


# ==================== 用户管理（管理员） ====================
@login_required
def admin_user_list(request):
    """用户列表"""
    user_info = get_or_create_user_info(request.user.username)
    
    # 获取Django用户
    from django.contrib.auth.models import User
    users = User.objects.all().order_by('-date_joined')
    
    context = {
        'user_info': user_info,
        'users': users,
    }
    return render(request, 'admin/user_list.html', context)


@login_required
def admin_user_create(request):
    """创建用户"""
    user_info = get_or_create_user_info(request.user.username)
    
    from django.contrib.auth.models import User
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        is_superuser = request.POST.get('is_superuser') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        
        if User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
            return redirect('admin_user_create')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_superuser=is_superuser,
            is_staff=is_staff,
        )
        
        # 创建对应的UserInfo
        UserInfo.objects.create(
            user_id=f'USER-{User.objects.count():03d}',
            user_name=username,
            team_name=request.POST.get('team_name', ''),
            contact_info=request.POST.get('contact_info', ''),
        )
        
        messages.success(request, f'用户 {username} 创建成功')
        return redirect('admin_user_list')
    
    context = {
        'user_info': user_info,
    }
    return render(request, 'admin/user_create.html', context)


@login_required
def admin_user_edit(request, user_id):
    """编辑用户"""
    user_info = get_or_create_user_info(request.user.username)
    from django.contrib.auth.models import User
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.email = request.POST.get('email', '')
        user.is_active = request.POST.get('is_active') == 'on'
        user.is_superuser = request.POST.get('is_superuser') == 'on'
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.save()
        
        # 更新UserInfo
        user_info_obj = UserInfo.objects.filter(user_name=user.username).first()
        if user_info_obj:
            user_info_obj.team_name = request.POST.get('team_name', '')
            user_info_obj.contact_info = request.POST.get('contact_info', '')
            user_info_obj.save()
        
        messages.success(request, f'用户 {user.username} 更新成功')
        return redirect('admin_user_list')
    
    user_info_obj = UserInfo.objects.filter(user_name=user.username).first()
    
    context = {
        'user_info': user_info,
        'user': user,
        'user_info_obj': user_info_obj,
    }
    return render(request, 'admin/user_edit.html', context)


@login_required
def admin_user_delete(request, user_id):
    """删除用户"""
    from django.contrib.auth.models import User
    user = get_object_or_404(User, id=user_id)
    
    # 不能删除自己
    if user.id == request.user.id:
        messages.error(request, '不能删除当前登录用户')
        return redirect('admin_user_list')
    
    # 删除对应的UserInfo
    UserInfo.objects.filter(user_name=user.username).delete()
    
    username = user.username
    user.delete()
    
    messages.success(request, f'用户 {username} 已删除')
    return redirect('admin_user_list')


@login_required
def admin_user_reset_password(request, user_id):
    """重置用户密码"""
    from django.contrib.auth.models import User
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('password')
        user.set_password(new_password)
        user.save()
        messages.success(request, f'用户 {user.username} 密码已重置')
        return redirect('admin_user_list')
    
    context = {
        'user_info': get_or_create_user_info(request.user.username),
        'user': user,
    }
    return render(request, 'admin/user_reset_password.html', context)


@login_required
def alarm_list(request):
    """告警中心"""
    user_info = get_or_create_user_info(request.user.username)
    today = date.today()
    
    today_reminders = DailyReminder.objects.filter(reminder_date=today, user_name=user_info)
    overdue_tasks = TaskInfo.objects.filter(
        plan_end_date__lt=today,
        task_status__in=['进行中', '未开始'],
        task_owner=user_info
    )
    
    email_enabled = SystemSettings.objects.filter(
        setting_type='email',
        setting_key='enable_notify',
        is_enabled=True
    ).exists()
    
    context = {
        'user_info': user_info,
        'today_reminders': today_reminders,
        'overdue_tasks': overdue_tasks,
        'email_enabled': email_enabled,
    }
    return render(request, 'alarm/list.html', context)


@login_required
def send_alarm_email(request):
    """发送告警邮件"""
    if request.method == 'POST':
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            email_settings = SystemSettings.objects.filter(setting_type='email')
            config = {s.setting_key: s.setting_value for s in email_settings}
            
            if not config.get('email_host') or not config.get('email_user'):
                return JsonResponse({'success': False, 'error': '邮件未配置'})
            
            user_info = get_or_create_user_info(request.user.username)
            today = date.today()
            
            overdue_count = TaskInfo.objects.filter(
                plan_end_date__lt=today,
                task_status__in=['进行中', '未开始']
            ).count()
            
            today_count = DailyReminder.objects.filter(reminder_date=today).count()
            
            subject = f'项目管理系统告警 - {today}'
            message = f'''
您好 {user_info.user_name}，

这是您的每日告警报告：

今日待办任务：{today_count} 项
逾期任务：{overdue_count} 项

请及时处理！

---
PMS项目管理系统
'''
            
            settings.EMAIL_HOST = config.get('email_host', 'smtp.qq.com')
            settings.EMAIL_PORT = int(config.get('email_port', 587))
            settings.EMAIL_HOST_USER = config.get('email_user', '')
            settings.EMAIL_HOST_PASSWORD = config.get('email_password', '')
            settings.EMAIL_USE_TLS = True
            settings.DEFAULT_FROM_EMAIL = config.get('email_from', config.get('email_user', ''))
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user_info.contact_info] if user_info.contact_info else [request.user.email],
                fail_silently=False,
            )
            
            return JsonResponse({'success': True, 'message': '邮件发送成功'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def help_index(request):
    """帮助文档首页"""
    categories = [
        {
            'id': 'project',
            'name': '项目管理',
            'icon': 'bi-folder',
            'items': [
                {'title': '创建项目', 'content': '点击"项目"→"新建项目"，填写项目名称、经理、开始/结束日期后保存。'},
                {'title': '项目状态', 'content': '项目状态分为：未开始、进行中、已完成、逾期未完结。系统自动根据日期判断。'},
                {'title': '甘特图', 'content': '甘特图展示项目和任务时间线，支持项目视图和任务视图切换。'},
            ]
        },
        {
            'id': 'task',
            'name': '任务管理',
            'icon': 'bi-list-task',
            'items': [
                {'title': '创建任务', 'content': '在项目详情页或任务列表中点击"新建任务"，关联项目并设置负责人。'},
                {'title': '任务状态', 'content': '任务状态：未开始、进行中、已完成、已逾期。'},
                {'title': '四象限', 'content': '按重要紧急程度将任务分为四个象限：重要紧急、重要不紧急、紧急不重要、不紧急不重要。'},
            ]
        },
        {
            'id': 'plan',
            'name': '周计划',
            'icon': 'bi-calendar-week',
            'items': [
                {'title': '创建计划', 'content': '周计划仅工作日可创建，支持为周一至周五设置任务。'},
                {'title': '休息日', 'content': '周六、周日默认为休息状态，不可编辑。'},
            ]
        },
        {
            'id': 'gantt',
            'name': '甘特图',
            'icon': 'bi-bar-chart-steps',
            'items': [
                {'title': '项目视图', 'content': '展示所有项目及其下属任务的时间线。'},
                {'title': '任务视图', 'content': '独立展示所有任务，可按项目筛选。'},
                {'title': '时间范围', 'content': '甘特图自动根据项目起止日期生成时间轴。'},
            ]
        },
        {
            'id': 'budget',
            'name': '预算成本',
            'icon': 'bi-cash-stack',
            'items': [
                {'title': '添加预算', 'content': '在预算管理中创建预算项目，关联具体项目。'},
                {'title': '费用报销', 'content': '记录各项费用支出，系统自动统计成本。'},
            ]
        },
        {
            'id': 'monitor',
            'name': '系统监控',
            'icon': 'bi-graph-up',
            'items': [
                {'title': '监控指标', 'content': '展示CPU、内存、磁盘、网络等系统资源使用情况。'},
                {'title': '实时更新', 'content': '数据实时刷新，显示最新系统状态。'},
            ]
        },
        {
            'id': 'dashboard',
            'name': '看板',
            'icon': 'bi-kanban',
            'items': [
                {'title': '数据展示', 'content': '实时展示项目数、任务完成率、工作量统计等。'},
                {'title': '配置数据源', 'content': '点击"配置数据源"可自定义显示模块和刷新间隔。'},
            ]
        },
        {
            'id': 'logs',
            'name': '日志',
            'icon': 'bi-journal-text',
            'items': [
                {'title': '操作日志', 'content': '记录用户的关键操作，如上传、修改等。'},
                {'title': '系统日志', 'content': '记录系统运行状态、错误、警告等信息。'},
                {'title': '筛选导出', 'content': '支持按类型、日期筛选日志内容，支持CSV/Excel导出。'},
            ]
        },
    ]
    
    selected_category = request.GET.get('category', 'project')
    selected_item = request.GET.get('item', '')
    
    return render(request, 'help/index.html', {
        'categories': categories,
        'selected_category': selected_category,
        'selected_item': selected_item,
    })


# AI相关视图函数

@login_required
def ai_dashboard(request):
    """AI功能仪表盘"""
    user_info = get_or_create_user_info(request.user.username)
    
    from pmsapp.services.ai_gateway import AIGateway
    gateway = AIGateway()
    ai_config = gateway.get_config()
    
    has_ai_config = ai_config is not None
    
    return render(request, 'ai/dashboard.html', {
        'user_info': user_info,
        'has_ai_config': has_ai_config,
    })


@login_required
def ai_chat_page(request):
    """AI助手页面"""
    user_info = get_or_create_user_info(request.user.username)
    return render(request, 'ai/chat.html', {
        'user_info': user_info,
    })


@login_required
def ai_risks_page(request):
    """风险预警页面"""
    user_info = get_or_create_user_info(request.user.username)
    
    from pmsapp.models import RiskAlert, ProjectInfo
    
    unresolved_alerts = RiskAlert.objects.filter(is_resolved=False).order_by('-created_at')[:50]
    resolved_alerts = RiskAlert.objects.filter(is_resolved=True).order_by('-resolved_at')[:20]
    projects = ProjectInfo.objects.all()
    
    risk_summary = {
        'critical': unresolved_alerts.filter(risk_level='critical').count(),
        'high': unresolved_alerts.filter(risk_level='high').count(),
        'medium': unresolved_alerts.filter(risk_level='medium').count(),
        'low': unresolved_alerts.filter(risk_level='low').count(),
    }
    
    return render(request, 'ai/risks.html', {
        'user_info': user_info,
        'unresolved_alerts': unresolved_alerts,
        'resolved_alerts': resolved_alerts,
        'projects': projects,
        'risk_summary': risk_summary,
    })


@login_required
def workflow_rules_page(request):
    """工作流规则管理页面"""
    user_info = get_or_create_user_info(request.user.username)
    
    from pmsapp.models import WorkflowRule, WorkflowLog
    
    rules = WorkflowRule.objects.all().order_by('-created_at')
    recent_logs = WorkflowLog.objects.all().order_by('-executed_at')[:30]
    
    return render(request, 'ai/workflow.html', {
        'user_info': user_info,
        'rules': rules,
        'recent_logs': recent_logs,
    })


# AI API视图函数

@login_required
def ai_chat_api(request):
    """AI对话API"""
    from pmsapp.services.ai_agent import AIAgent
    
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not message:
            return JsonResponse({'success': False, 'error': '消息不能为空'})
        
        user_id = get_or_create_user_info(request.user.username).user_id
        agent = AIAgent()
        response = agent.chat(user_id, message, session_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'content': response.content,
                'session_id': response.session_id,
            }
        })
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@login_required
def ai_chat_history_api(request):
    """AI对话历史API"""
    from pmsapp.services.ai_agent import AIAgent
    
    session_id = request.GET.get('session_id')
    user_id = get_or_create_user_info(request.user.username).user_id
    agent = AIAgent()
    
    if session_id:
        history = agent._get_chat_history(user_id, session_id)
        return JsonResponse({'success': True, 'data': history})
    else:
        sessions = agent.get_chat_sessions(user_id)
        return JsonResponse({'success': True, 'data': sessions})


@login_required
def ai_chat_clear_api(request):
    """清除AI对话历史API"""
    from pmsapp.services.ai_agent import AIAgent
    
    session_id = request.GET.get('session_id')
    user_id = get_or_create_user_info(request.user.username).user_id
    agent = AIAgent()
    
    success = agent.clear_chat_history(user_id, session_id)
    return JsonResponse({'success': success})


@login_required
def ai_config_api(request):
    """AI配置API"""
    from pmsapp.services.ai_gateway import AIGateway
    gateway = AIGateway()
    
    if request.method == "GET":
        provider = request.GET.get('provider')
        config = gateway.get_config(provider)
        
        if config:
            config['api_key'] = '********' if config.get('api_key') else ''
        
        return JsonResponse({'success': True, 'data': config})
    
    elif request.method == "POST":
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
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@login_required
def ai_config_validate_api(request):
    """验证AI配置API"""
    from pmsapp.services.ai_gateway import AIGateway
    
    if request.method == "POST":
        data = json.loads(request.body)
        gateway = AIGateway()
        is_valid, message = gateway.validate_config(data)
        return JsonResponse({'success': True, 'data': {'valid': is_valid, 'message': message}})
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@login_required
def ai_analyze_risk_api(request):
    """分析项目风险API"""
    from pmsapp.services.ai_agent import AIAgent
    
    if request.method == "POST":
        data = json.loads(request.body)
        project_id = data.get('project_id')
        
        if not project_id:
            return JsonResponse({'success': False, 'error': '项目ID不能为空'})
        
        user_id = get_or_create_user_info(request.user.username).user_id
        agent = AIAgent()
        report = agent.analyze_risk(project_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'project_id': report.project_id,
                'risk_level': report.risk_level,
                'risks': report.risks,
                'suggestions': report.suggestions,
            }
        })
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@login_required
def ai_generate_report_api(request):
    """生成报告API"""
    from pmsapp.services.ai_agent import AIAgent
    
    if request.method == "POST":
        data = json.loads(request.body)
        report_type = data.get('report_type', 'weekly')
        
        user_id = get_or_create_user_info(request.user.username).user_id
        agent = AIAgent()
        report = agent.generate_report(user_id, report_type)
        
        return JsonResponse({
            'success': True,
            'data': {
                'report_type': report_type,
                'content': report,
            }
        })
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@login_required
def ai_recommend_task_api(request):
    """推荐任务分配API"""
    from pmsapp.services.ai_agent import AIAgent
    
    if request.method == "POST":
        data = json.loads(request.body)
        task_data = {
            'project_id': data.get('project_id'),
            'task_type': data.get('task_type'),
            'expected_hours': data.get('expected_hours'),
        }
        
        agent = AIAgent()
        recommendations = agent.recommend_assignee(task_data)
        
        return JsonResponse({'success': True, 'data': recommendations})
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@login_required
def risk_alerts_api(request):
    """获取风险预警列表API"""
    from pmsapp.models import RiskAlert
    
    project_id = request.GET.get('project_id')
    resolved = request.GET.get('resolved', 'false').lower() == 'true'
    
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
                'created_at': a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]
    })


@login_required
def risk_check_api(request):
    """触发风险检测API"""
    from pmsapp.services.analyzer import RiskAnalyzer
    
    if request.method == "POST":
        data = json.loads(request.body)
        check_types = data.get('types', ['overdue', 'budget', 'schedule'])
        
        analyzer = RiskAnalyzer()
        results = {}
        
        if 'overdue' in check_types:
            results['overdue'] = [a.to_dict() for a in analyzer.check_overdue_tasks()]
        
        if 'budget' in check_types:
            results['budget'] = [a.to_dict() for a in analyzer.check_budget_risk()]
        
        if 'schedule' in check_types:
            results['schedule'] = [a.to_dict() for a in analyzer.check_schedule_risk()]
        
        return JsonResponse({'success': True, 'data': results})
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@login_required
def workflow_rules_api(request):
    """工作流规则管理API"""
    from pmsapp.services.workflow_engine import WorkflowEngine, WorkflowRule
    
    engine = WorkflowEngine()
    
    if request.method == "GET":
        trigger_type = request.GET.get('trigger_type')
        rules = engine.get_rules(trigger_type)
        return JsonResponse({'success': True, 'data': [r.to_dict() for r in rules]})
    
    elif request.method == "POST":
        data = json.loads(request.body)
        user_id = get_or_create_user_info(request.user.username).user_id
        
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
    
    elif request.method == "PUT":
        data = json.loads(request.body)
        rule_id = data.get('rule_id')
        
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
    
    elif request.method == "DELETE":
        rule_id = request.GET.get('rule_id')
        success = engine.delete_rule(rule_id)
        return JsonResponse({'success': success})
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})


@login_required
def workflow_logs_api(request):
    """获取工作流执行日志API"""
    from pmsapp.services.workflow_engine import WorkflowEngine
    
    engine = WorkflowEngine()
    rule_id = request.GET.get('rule_id')
    limit = int(request.GET.get('limit', 50))
    
    logs = engine.get_execution_log(rule_id, limit)
    
    return JsonResponse({'success': True, 'data': logs})


@login_required
def risk_alert_resolve_api(request, alert_id):
    """标记风险预警为已解决API"""
    from pmsapp.models import RiskAlert
    from datetime import datetime
    
    if request.method == "POST":
        try:
            alert = RiskAlert.objects.get(alert_id=alert_id)
            alert.is_resolved = True
            alert.resolved_at = datetime.now()
            alert.save()
            return JsonResponse({'success': True})
        except RiskAlert.DoesNotExist:
            return JsonResponse({'success': False, 'error': '预警不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})
