#coding: utf-8
from __future__ import unicode_literals, absolute_import
from django.views.generic import ListView, DetailView

from remind.models import Remind


class RemindListView(ListView):
    allow_empty = True
    model = Remind
    context_object_name = 'reminds'
    ordering = '-time'


class RemindDetailView(DetailView):
    model = Remind
    context_object_name = 'remind'
