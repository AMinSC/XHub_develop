from django.contrib import admin
from django.urls import path, include

# channels jwt
from django_channels_jwt.views import AsgiValidateTokenView

# swagger
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# img module import
from django.conf.urls.static import static
from django.conf import settings

# swagger
schema_view = get_schema_view(
    openapi.Info(
        title="Xhub API",
        default_version="v1",
        description="Xhub의 API 문서입니다.",
        # terms_of_service="https://github.com/ExerciseHub/XHub",
        # contact=openapi.Contact(email=""),
        license=openapi.License(name="MIT license"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # channels jwt
    path("auth_for_ws_connection/", AsgiValidateTokenView.as_view()),
    
    path('player/', include('player.urls')),
    path('quickmatch/', include('quickmatch.urls')),
    path('board/', include('board.urls')),
]

#img
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
