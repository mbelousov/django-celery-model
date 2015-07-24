from django.contrib import admin


class TaskModelAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return self.list_display + ('task_status',)

    def task_status(self, instance):
        if instance.has_running_task:
            return "Running"
        return "Ready"
