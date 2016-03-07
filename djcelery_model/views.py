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
        response_object = {
            'status': '',
            'tasks': [],
        }
        try:
            task_limit = 10 * 60  # 10 minutes
            for t in self.object.tasks.running():
                timediff = datetime.utcnow().replace(tzinfo=utc) - t.created_at
                res = AsyncResult(t.task_id)
                try:
                    res_state = res.state
                except Exception as e:
                    print e
                    print "WRONG STATE"
                    t.delete()
                    continue

                if timediff.total_seconds() > task_limit and \
                        (t.state == ModelTaskMetaState.PENDING or
                                 res.state == states.PENDING):
                    t.delete()
                    continue
                response_object['tasks'].append({
                    'task_id': t.task_id,
                    'task_name': t.task_name,
                    'object_id': t.object_id,
                    'block_ui': t.block_ui,
                    'created_at': str(t.created_at),
                })
            if len(response_object['tasks']) > 0:
                response_object['status'] = 'running'
            else:
                response_object['status'] = 'ready'
        except Exception, e:
            response_object['status'] = 'error'
            response_object['error_message'] = str(e)
        return response_object

    def render_to_response(self, context, *args, **kwargs):
        response_object = self.get_response_object()
        return HttpResponse(json.dumps(response_object),
                            content_type="application/json")
