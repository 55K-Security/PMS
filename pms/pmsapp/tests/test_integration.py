from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from datetime import date, timedelta
import os, tempfile, shutil

from pmsapp.models import UserInfo, ProjectInfo, TaskInfo


class SystemIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a real Django user for auth and ensure it's staff for privileged actions
        self.user = User.objects.create_user(username='admin', email='admin@example.com', password='Admin@2024')
        self.user.is_staff = True
        self.user.save()

    def test_login_page_loads(self):
        resp = self.client.get('/login/')
        self.assertEqual(resp.status_code, 200)

    def test_login_with_captcha_success(self):
        # get captcha to populate session
        self.client.get('/captcha/')
        captcha = self.client.session.get('captcha_code', '')
        self.assertIsNotNone(captcha)
        resp = self.client.post('/login/', {
            'username': 'admin',
            'password': 'Admin@2024',
            'captcha': captcha,
        }, follow=True)
        # Could redirect to index on success
        self.assertIn(resp.status_code, (200, 302))
        self.assertTrue(resp.context['user'].is_authenticated)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_version_upgrade_upload_saves_files(self):
        self.client.login(username='admin', password='Admin@2024')
        patch = SimpleUploadedFile('patch.bin', b'patch', content_type='application/octet-stream')
        upgrade = SimpleUploadedFile('upgrade.bin', b'upgrade', content_type='application/octet-stream')
        resp = self.client.post('/settings/version_upgrade/', {'patch_file': patch, 'upgrade_file': upgrade})
        self.assertIn(resp.status_code, (200, 302))
        ver_dir = os.path.join(settings.MEDIA_ROOT, 'version_upgrades')
        self.assertTrue(os.path.isdir(ver_dir))
        self._cleanup_dir(ver_dir)

    def test_version_upgrade_access_denied_for_non_staff(self):
        # create non-staff user
        guest = User.objects.create_user(username='guest', email='guest@example.com', password='guest123')
        self.client.login(username='guest', password='guest123')
        patch = SimpleUploadedFile('patch.bin', b'patch', content_type='application/octet-stream')
        upgrade = SimpleUploadedFile('upgrade.bin', b'upgrade', content_type='application/octet-stream')
        resp = self.client.post('/settings/version_upgrade/', {'patch_file': patch, 'upgrade_file': upgrade})
        self.assertEqual(resp.status_code, 403)

    def test_version_upgrade_reject_invalid_extension(self):
        self.client.login(username='admin', password='Admin@2024')
        patch = SimpleUploadedFile('patch.txt', b'patch', content_type='text/plain')
        upgrade = SimpleUploadedFile('upgrade.bin', b'upgrade', content_type='application/octet-stream')
        resp = self.client.post('/settings/version_upgrade/', {'patch_file': patch, 'upgrade_file': upgrade})
        self.assertIn(resp.status_code, (200,))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_ui_customize_upload(self):
        self.client.login(username='admin', password='Admin@2024')
        login_bg = SimpleUploadedFile('bg.jpg', b'bg', content_type='image/jpeg')
        logo = SimpleUploadedFile('logo.png', b'logo', content_type='image/png')
        resp = self.client.post('/settings/ui_customize/', {'login_background': login_bg, 'system_logo': logo})
        self.assertIn(resp.status_code, (200, 302))
        up_dir = os.path.join(settings.MEDIA_ROOT, 'ui')
        self.assertTrue(os.path.isdir(up_dir))
        files = os.listdir(up_dir)
        self.assertGreaterEqual(len(files), 2)
        self._cleanup_dir(up_dir)

    def test_monitor_and_dashboard_views(self):
        self.client.login(username='admin', password='Admin@2024')
        resp1 = self.client.get('/monitor/')
        resp2 = self.client.get('/dashboard-big/')
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)

    def test_gantt_view(self):
        self.client.login(username='admin', password='Admin@2024')
        # Create a minimal project/task to populate gantt
        u = UserInfo.objects.create(user_id='USER-001', user_name='admin', team_name='', contact_info='')
        p = ProjectInfo.objects.create(
            project_id='P001', project_name='Test Project', project_manager=u,
            start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        TaskInfo.objects.create(
            task_id='TASK-P001-001', project=p, key_content_name='Design', priority_level='优先级1',
            task_owner=u, plan_start_date=date.today(), plan_end_date=date.today() + timedelta(days=5),
            task_cycle=5, time_progress=0.0, task_status='未开始'
        )
        resp = self.client.get('/gantt/')
        self.assertEqual(resp.status_code, 200)

    def test_logs_upgrade_view(self):
        # ensure admin can access logs upgrade page
        self.client.login(username='admin', password='Admin@2024')
        resp = self.client.get('/settings/logs_upgrade/')
        self.assertIn(resp.status_code, (200, 301, 302))

    def test_logs_upgrade_export_excel(self):
        import importlib
        if importlib.util.find_spec('openpyxl') is None:
            self.skipTest('openpyxl not installed')
        self.client.login(username='admin', password='Admin@2024')
        resp = self.client.get('/settings/logs_upgrade/export_excel/')
        self.assertIn(resp.status_code, (200, 201, 202))
    def _cleanup_dir(self, path):
        try:
            import shutil
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass
