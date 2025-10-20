from django.urls import path
from rest_framework.routers import DefaultRouter
from tasks.views import (
    TaskViewSet,
    TaskExecutionViewSet,
    TaskLogViewSet
)

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)
router.register(r'task-executions', TaskExecutionViewSet)
router.register(r'task-logs', TaskLogViewSet)

urlpatterns = [
    # 其他任务相关的URL路径
] + router.urls