from django.views.generic.detail import BaseDetailView
from django.http import HttpResponse
import json
from datetime import datetime
from django.utils.timezone import utc
from .models import ModelTaskMetaState
from celery import states
from celery.result import AsyncResult


class ModelTaskStatusView(BaseDetailView):
    def get_response_object(self):
        task_status = self.object.get_task_status()
        return task_status

    def render_to_response(self, context, *args, **kwargs):
        response_object = self.get_response_object()
        return HttpResponse(json.dumps(response_object),
                            content_type="application/json")
