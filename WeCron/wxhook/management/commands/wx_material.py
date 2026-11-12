# coding: utf-8

import json
from django.core.management import BaseCommand
from common import wechat_client


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write(
            json.dumps(wechat_client.material.batchget('image'),
                       indent=2,
                       ensure_ascii=False))