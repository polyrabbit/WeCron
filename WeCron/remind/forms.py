#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from django import forms
from .models import Remind


logger = logging.getLogger(__name__)


class RemindForm(forms.ModelForm):
    class Meta:
        model = Remind
        fields = ['time', 'defer', 'desc', 'event']

    defer = forms.CharField()

    def clean_defer(self):
        units = {'周': 7*24*60, '天': 60*24, '小时': 60, '分钟': 1}
        try:
            # self.cleaned_data['defer'] should be '1 小时'
            before, minutes, u = self.cleaned_data['defer'].split(' ')
            return int(minutes) * units[u] * (-1 if before == '提前' else 1)
        except Exception as e:
            logger.info('Error in parsing defer', e)
            return 0

    def save(self, commit=True):
        self.instance.done = False
        return super(RemindForm, self).save(commit)