from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ItemViewSet, RegisterAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'items', ItemViewSet, basename='item')


urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterAPIView.as_view({'post': 'create'}), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]