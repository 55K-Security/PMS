from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pmsapp', '0005_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='upgradelog',
            name='action_source',
            field=models.CharField(max_length=64, default='web'),
        ),
        migrations.AddField(
            model_name='upgradelog',
            name='ip_address',
            field=models.GenericIPAddressField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='upgradelog',
            name='upgrade_version',
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
    ]
