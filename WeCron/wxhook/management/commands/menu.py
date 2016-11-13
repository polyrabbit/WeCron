# coding: utf-8
from __future__ import unicode_literals, absolute_import

import json
from django.core.management import BaseCommand
from common import wechat_client


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('new_menu', nargs='*')

    def handle(self, *args, **options):
        if not options.get('new_menu'):
            self.stdout.write(
                    json.dumps(
                        wechat_client.menu.get(),
                        ensure_ascii=False))
        else:
            new_menu = json.loads(options['new_menu'][0])
            self.stdout.write(
                    json.dumps(wechat_client.menu.create(new_menu),
                    indent=2,
                    ensure_ascii=False))
