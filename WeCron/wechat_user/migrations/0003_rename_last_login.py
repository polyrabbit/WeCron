from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wechat_user', '0002_django5_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='wechatuser',
            old_name='last_login',
            new_name='last_message_time',
        ),
        migrations.AlterField(
            model_name='wechatuser',
            name='last_message_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='最后发消息时间'),
        ),
    ]
