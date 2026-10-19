from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db.models import Prefetch
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import Role

from .models import Activity, Notification
from .registry import TRACKED, by_key, model_of
from .serializers import ActivityCreateSerializer, ActivitySerializer, NotificationSerializer, PersonSerializer


def _activities():
    return Activity.objects.select_related("author", "content_type").prefetch_related(
        GenericPrefetch("target", _target_querysets())
    )


def _target_querysets():
    """Документы для GenericPrefetch: подпись рецептуры берёт название продукта — сразу подтягиваем его."""
    querysets = []
    for tracked in TRACKED:
        qs = model_of(tracked)._default_manager.all()
        if tracked.model == "recipes.Recipe":
            qs = qs.select_related("product")
        querysets.append(qs)
    return querysets


class ActivityViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    Живая лента и таймлайны документов.

    - `GET ?target=sales.salesorder&target_id=5` — таймлайн документа (события и комментарии);
    - `GET` без target — общая лента; `?kind=comment&kind=post` — только записи нужных видов, `?type=` — тип документа;
    - `POST {text, target, target_id}` — комментарий к документу, без target — сообщение в ленту;
    - `DELETE` — удалить свой комментарий или сообщение (администратор — любой).
    """

    serializer_class = ActivitySerializer

    def get_queryset(self):
        qs = _activities()
        params = self.request.query_params
        if self.action == "list":
            if params.get("target"):
                tracked = self._tracked(params["target"])
                ct = ContentType.objects.get_for_model(model_of(tracked))
                qs = qs.filter(content_type=ct, object_id=params.get("target_id") or 0)
            if params.get("type"):
                qs = qs.filter(content_type=ContentType.objects.get_for_model(model_of(self._tracked(params["type"]))))
            if kinds := params.getlist("kind"):
                qs = qs.filter(kind__in=kinds)
        return qs

    @staticmethod
    def _tracked(key):
        tracked = by_key(key)
        if not tracked:
            raise ValidationError({"target": f"Документы «{key}» не ведут ленту."})
        return tracked

    def create(self, request, *args, **kwargs):
        data = ActivityCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        text, key, target_id = data.validated_data["text"], data.validated_data.get("target"), data.validated_data.get("target_id")
        target = None
        if key:
            model = model_of(self._tracked(key))
            target = model._default_manager.filter(pk=target_id).first() if target_id else None
            if target is None:
                raise ValidationError({"target_id": "Документ не найден."})
        activity = Activity.objects.create(
            kind=Activity.Kind.COMMENT if target else Activity.Kind.POST, target=target, author=request.user, text=text,
        )
        activity = self.get_queryset().get(pk=activity.pk)
        return Response(self.get_serializer(activity).data, status=status.HTTP_201_CREATED)

    @action(detail=False, pagination_class=None)
    def people(self, request):
        """Активные пользователи — для подсказки @упоминаний."""
        users = get_user_model().objects.filter(is_active=True).order_by("first_name", "username")
        return Response(PersonSerializer(users, many=True).data)

    def perform_destroy(self, activity):
        if activity.kind not in (Activity.Kind.COMMENT, Activity.Kind.POST):
            raise PermissionDenied("События документов удалять нельзя.")
        if activity.author_id != self.request.user.pk and self.request.user.role != Role.ADMIN:
            raise PermissionDenied("Удалить можно только свою запись.")
        activity.delete()


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Уведомления текущего пользователя (колокольчик).

    - `GET` — список, новые сверху; `?unread=1` — только непрочитанные;
    - `GET count/` — число непрочитанных (опрашивается шапкой);
    - `POST {id}/read/`, `POST read_all/` — отметить прочитанными.
    """

    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user).prefetch_related(
            Prefetch("activity", queryset=_activities())
        )
        if self.request.query_params.get("unread") in ("1", "true"):
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=False)
    def count(self, request):
        return Response({"unread": Notification.objects.filter(recipient=request.user, is_read=False).count()})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        updated = Notification.objects.filter(recipient=request.user, pk=pk).update(is_read=True)
        return Response({"read": updated})

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        return Response({"read": Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)})
