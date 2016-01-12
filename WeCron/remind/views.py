#coding: utf-8
from __future__ import unicode_literals, absolute_import
from django.views.generic import ListView, DetailView
from django.utils import timezone

from remind.models import Remind


class RemindListView(ListView):
    context_object_name = 'reminds'

    def get_queryset(self):
        return Remind.objects.filter(time__date__gte=timezone.now()).order_by('time')


class RemindDetailView(DetailView):
    model = Remind
    context_object_name = 'remind'
