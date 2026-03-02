from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pmsapp', '0002_projectfile'),
    ]

    operations = [
        migrations.CreateModel(
            name='UpgradeLog',
            fields=[
                ('log_id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('upload_time', models.DateTimeField(auto_now_add=True)),
                ('patch_file_name', models.CharField(max_length=255, blank=True, null=True)),
                ('upgrade_file_name', models.CharField(max_length=255, blank=True, null=True)),
                ('status', models.CharField(max_length=32, default='SUCCESS')),
                ('notes', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(null=True, blank=True, on_delete=models.SET_NULL, to='pmsapp.UserInfo')),
            ],
            options={
                'db_table': 't_upgrade_log',
                'verbose_name': '升级日志',
                'verbose_name_plural': '升级日志',
            },
        ),
    ]
