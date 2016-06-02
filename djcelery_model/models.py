# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet
from django.contrib.contenttypes.models import ContentType
from datetime import datetime
from django.utils import timezone
from django.conf import settings
import logging

try:
    # Django >= 1.7
    from django.contrib.contenttypes.fields import GenericForeignKey, \
        GenericRelation
except ImportError:
    from django.contrib.contenttypes.generic import GenericForeignKey, \
        GenericRelation

from celery.result import BaseAsyncResult
from celery.utils import uuid
from celery import signals

logger = logging.getLogger('')
DJCELERY_MODEL_SETTINGS = getattr(settings, 'DJCELERY_MODEL', {})


class ModelTaskMetaState(object):
    PENDING = 0
    STARTED = 1
    RETRY = 2
    FAILURE = 3
    SUCCESS = 4
    IGNORED = 5

    @classmethod
    def lookup(cls, state):
        return getattr(cls, state, cls.FAILURE)


class ModelTaskMetaFilterMixin(object):
    def current_running_task(self):
        try:
            return self.running().latest('pk')
        except ModelTaskMeta.DoesNotExist:
            return None

    def last_ready_task(self):
        try:
            return self.ready().latest(
                'updated_at')
        except ModelTaskMeta.DoesNotExist:
            return None

    def pending(self):
        return self.filter(state=ModelTaskMetaState.PENDING)

    def started(self):
        return self.filter(state=ModelTaskMetaState.STARTED)

    def retrying(self):
        return self.filter(state=ModelTaskMetaState.RETRY)

    def failed(self):
        return self.filter(state=ModelTaskMetaState.FAILURE)

    def successful(self):
        return self.filter(state=ModelTaskMetaState.SUCCESS)

    def running(self):
        return self.filter(Q(state=ModelTaskMetaState.PENDING) |
                           Q(state=ModelTaskMetaState.STARTED) |
                           Q(state=ModelTaskMetaState.RETRY))

    def ready(self):
        return self.filter(Q(state=ModelTaskMetaState.FAILURE) |
                           Q(state=ModelTaskMetaState.SUCCESS))

    def skipped(self):
        return self.filter(state=ModelTaskMetaState.IGNORED)


class ModelTaskMetaQuerySet(ModelTaskMetaFilterMixin, QuerySet):
    pass


class ModelTaskMetaManager(ModelTaskMetaFilterMixin, models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return ModelTaskMetaQuerySet(self.model, using=self._db)


class ModelTaskMeta(models.Model):
    STATES = (
        (ModelTaskMetaState.PENDING, 'PENDING'),
        (ModelTaskMetaState.STARTED, 'STARTED'),
        (ModelTaskMetaState.RETRY, 'RETRY'),
        (ModelTaskMetaState.FAILURE, 'FAILURE'),
        (ModelTaskMetaState.SUCCESS, 'SUCCESS'),
        (ModelTaskMetaState.IGNORED, 'IGNORED'),
    )

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    task_id = models.CharField(max_length=255, unique=True)
    task_name = models.CharField(max_length=255, blank=True)
    state = models.PositiveIntegerField(choices=STATES,
                                        default=ModelTaskMetaState.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    block_ui = models.BooleanField(default=False)
    objects = ModelTaskMetaManager()

    def __unicode__(self):
        return u'%s: %s' % (self.task_id, dict(self.STATES)[self.state])

    @property
    def result(self):
        return ModelAsyncResult(self.task_id)


class ModelAsyncResult(BaseAsyncResult):
    def forget(self):
        ModelTaskMeta.objects.filter(task_id=self.id).delete()
        return super(ModelAsyncResult, self).forget()


class TaskFilterMixin(object):
    def with_tasks(self):
        return self.filter(tasks__state__isnull=False)

    def with_pending_tasks(self):
        return self.filter(tasks__state=ModelTaskMetaState.PENDING)

    def with_started_tasks(self):
        return self.filter(tasks__state=ModelTaskMetaState.STARTED)

    def with_retrying_tasks(self):
        return self.filter(tasks__state=ModelTaskMetaState.RETRY)

    def with_failed_tasks(self):
        return self.filter(tasks__state=ModelTaskMetaState.FAILURE)

    def with_successful_tasks(self):
        return self.filter(tasks__state=ModelTaskMetaState.SUCCESS)

    def with_running_tasks(self):
        return self.filter(Q(tasks__state=ModelTaskMetaState.PENDING) |
                           Q(tasks__state=ModelTaskMetaState.STARTED) |
                           Q(tasks__state=ModelTaskMetaState.RETRY))

    def with_ready_tasks(self):
        return self.filter(Q(tasks__state=ModelTaskMetaState.FAILURE) |
                           Q(tasks__state=ModelTaskMetaState.SUCCESS))

    def without_tasks(self):
        return self.exclude(tasks__state__isnull=False)

    def without_pending_tasks(self):
        return self.exclude(tasks__state=ModelTaskMetaState.PENDING)

    def without_started_tasks(self):
        return self.exclude(tasks__state=ModelTaskMetaState.STARTED)

    def without_retrying_tasks(self):
        return self.exclude(tasks__state=ModelTaskMetaState.RETRY)

    def without_failed_tasks(self):
        return self.exclude(tasks__state=ModelTaskMetaState.FAILURE)

    def without_successful_tasks(self):
        return self.exclude(tasks__state=ModelTaskMetaState.SUCCESS)

    def without_running_tasks(self):
        return self.exclude(Q(tasks__state=ModelTaskMetaState.PENDING) |
                            Q(tasks__state=ModelTaskMetaState.STARTED) |
                            Q(tasks__state=ModelTaskMetaState.RETRY))

    def without_ready_tasks(self):
        return self.exclude(Q(tasks__state=ModelTaskMetaState.FAILURE) |
                            Q(tasks__state=ModelTaskMetaState.SUCCESS))


class TaskQuerySet(TaskFilterMixin, QuerySet):
    pass


class TaskManager(TaskFilterMixin, models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return TaskQuerySet(self.model, using=self._db)


class TaskMixin(models.Model):
    tasks = GenericRelation(ModelTaskMeta)

    objects = TaskManager()

    class Meta:
        abstract = True

    @property
    def has_running_task(self):
        return self.tasks.running().exists()

    @property
    def has_ready_task(self):
        return self.tasks.ready().exists()

    @property
    def last_ready_task(self):
        return self.tasks.last_ready_task()

    @property
    def current_running_task(self):
        return self.tasks.current_running_task()

    def get_task_status(self, pending_task_timeout=0,
                        non_block_ui_timeout=0):
        status_obj = {

        }

        if pending_task_timeout <= 0:
            pending_task_timeout = DJCELERY_MODEL_SETTINGS.get(
                'PENDING_TASK_TIMEOUT', 10 * 60)
        if non_block_ui_timeout <= 0:
            non_block_ui_timeout = DJCELERY_MODEL_SETTINGS.get(
                'NON_BLOCK_UI_TIMEOUT', 1 * 60)

        last_ready_task = self.last_ready_task

        # remove old NOT RUNNING tasks
        old_ready_tasks = self.tasks.ready()
        if last_ready_task:
            old_ready_tasks = old_ready_tasks.exclude(pk=last_ready_task.pk)
        rn, _ = old_ready_tasks.delete()
        removed_n, _ = self.tasks.skipped().delete()
        removed_n += rn
        if removed_n > 0:
            logger.info("%d old tasks removed for %s" % (removed_n, self))

        # remove zombie tasks
        for t in self.tasks.running():
            timediff = datetime.utcnow().replace(tzinfo=timezone.utc) - \
                       t.created_at
            res = ModelAsyncResult(t.task_id)
            try:
                res_state = res.state
            except Exception as e:
                res.forget()
                logger.error("Task %s: wrong state, forget: %s" % (t, e))
                continue
            res_state = ModelTaskMetaState.lookup(res_state)
            if t.state != res_state:
                t.state = res_state
                t.save()
                logger.warn("Task %s state changed (mismatch)" % t)
            elapsed = timediff.total_seconds()
            if elapsed > pending_task_timeout and \
                    (t.state == ModelTaskMetaState.PENDING):
                t.delete()
                logger.warn(
                    "Task %s removed: pending for %s" % (t, elapsed))
                continue
            if not t.block_ui and t.state == ModelTaskMetaState.STARTED \
                    and elapsed > non_block_ui_timeout:
                t.block_ui = True
                t.save()
                logger.warn(
                    "Task %s removed: pending for %s" % (t, elapsed))

        if self.has_running_task:
            status = "busy"
            current_task = self.current_running_task
            running_time = datetime.utcnow().replace(tzinfo=timezone.utc) \
                           - current_task.created_at
            status_obj['running_task'] = {
                'task_id': current_task.task_id,
                'task_name': current_task.task_name,
                'state': current_task.get_state_display(),
                'created_at': current_task.created_at,
                'execution_time': running_time,
            }
        else:
            status = "ready"

        status_obj['status'] = status
        if last_ready_task:
            last_task_result = last_ready_task.result.result
            execution_time = last_ready_task.updated_at - last_ready_task.created_at

            status_obj['last_ready_task'] = {
                'task_id': last_ready_task.task_id,
                'task_name': last_ready_task.task_name,
                'state': last_ready_task.get_state_display(),
                'created_at': last_ready_task.created_at,
                'updated_at': last_ready_task.updated_at,
            }
            status_obj['last_ready_task']['execution_time'] = execution_time

            if isinstance(last_task_result, Exception):
                status_obj['last_ready_task']['error_message'] = str(
                    last_task_result)
            else:
                status_obj['last_ready_task']['result'] = str(
                    last_task_result)
        return status_obj

    def apply_async(self, task, *args, **kwargs):
        if 'task_id' in kwargs:
            task_id = kwargs['task_id']
        else:
            task_id = uuid()
        block_ui = kwargs.get('block_ui', False)
        try:
            taskmeta = ModelTaskMeta.objects.get(task_id=task_id)
            taskmeta.content_object = self
            taskmeta.block_ui = block_ui
            taskmeta.task_name = task.name
            forget_if_ready(BaseAsyncResult(task_id))
        except ModelTaskMeta.DoesNotExist:
            taskmeta = ModelTaskMeta(task_id=task_id, content_object=self,
                                     block_ui=block_ui, task_name=task.name)
        taskmeta.save()
        return task.apply_async(args=args, kwargs=kwargs, task_id=task_id)

    def get_task_results(self):
        return map(lambda x: x.result, self.tasks.all())

    def get_task_result(self, task_id):
        return self.tasks.get(task_id=task_id).result

    def clear_task_results(self):
        map(forget_if_ready, self.get_task_results())

    def clear_task_result(self, task_id):
        forget_if_ready(self.get_task_result(task_id))


def forget_if_ready(async_result):
    if async_result and async_result.ready():
        async_result.forget()


@signals.after_task_publish.connect
def handle_after_task_publish(sender=None, body=None, **kwargs):
    if body and 'id' in body:
        queryset = ModelTaskMeta.objects.filter(task_id=body['id'])
        queryset.update(state=ModelTaskMetaState.PENDING,
                        updated_at=timezone.now())


@signals.task_prerun.connect
def handle_task_prerun(sender=None, task_id=None, **kwargs):
    if task_id:
        queryset = ModelTaskMeta.objects.filter(task_id=task_id)
        queryset.update(state=ModelTaskMetaState.STARTED,
                        updated_at=timezone.now())


@signals.task_postrun.connect
def handle_task_postrun(sender=None, task_id=None, state=None, **kwargs):
    if task_id and state:
        queryset = ModelTaskMeta.objects.filter(task_id=task_id)
        queryset.update(state=ModelTaskMetaState.lookup(state),
                        updated_at=timezone.now())


@signals.task_revoked.connect
def handle_task_revoked(sender=None, request=None, **kwargs):
    if request and request.id:
        queryset = ModelTaskMeta.objects.filter(task_id=request.id)
        queryset.delete()
