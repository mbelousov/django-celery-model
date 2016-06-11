WORKER_OFFLINE = 0
WORKER_READY = 1
WORKER_BUSY = 2
WORKER_ERROR = 3
WORKER_STATUS_CHOICES = (
    (WORKER_OFFLINE, 'offline'),
    (WORKER_READY, 'ready'),
    (WORKER_BUSY, 'busy'),
    (WORKER_ERROR, 'error'),

)
WORKER_ERROR_STATUSES = (WORKER_OFFLINE, WORKER_ERROR)

def get_worker_status_display(status):
    for status_code, status_display in WORKER_STATUS_CHOICES:
        if status_code == status:
            return status_display
    return None


def get_worker_status():
    status_message = None
    try:
        status = WORKER_READY

        from celery.task.control import inspect
        insp = inspect()

        if insp.active():
            status = WORKER_READY
        else:
            status = WORKER_OFFLINE
            status_message = "No running Celery workers were found."
    except IOError as e:
        from errno import errorcode
        status_message = "Error connecting to the backend: " + str(e)
        if len(e.args) > 0 and errorcode.get(e.args[0]) == 'ECONNREFUSED':
            status_message += ' Check that the RabbitMQ server is running.'
        status = WORKER_OFFLINE
    except ImportError as e:
        status = WORKER_ERROR
        status_message = e.message

    d = {
        'status_code': status,
        'status': get_worker_status_display(status)
    }
    if status_message:
        d['status_message'] = status_message
    return d
