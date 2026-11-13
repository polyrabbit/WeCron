from django.db import migrations


def fix_sst(apps, schema_editor):
    # The web settings offered 'SST', which isn't an IANA zone and always fell back to the default one
    apps.get_model('wechat_user', 'WechatUser').objects.filter(timezone='SST').update(timezone='Asia/Shanghai')


class Migration(migrations.Migration):

    dependencies = [
        ('wechat_user', '0004_unionid'),
    ]

    operations = [
        migrations.RunPython(fix_sst, migrations.RunPython.noop),
    ]
