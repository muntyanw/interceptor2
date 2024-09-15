from django.urls import path
from interceptor import views
from django.conf.urls.static import static
import os
from django.conf import settings

urlpatterns = [
    path('telegram_auth/', views.telegram_auth, name='telegram_auth'),
    path('', views.start_client_view, name='start_client'),
    path('messages', views.message_list_and_edit, name='message_list_and_edit'),
    path('edit/<int:edit_pk>/', views.message_list_and_edit, name='message_list_and_edit'),
    path('send/<int:pk>/<str:chat_id>/', views.send_message, name='send_message'),
    path('remove_file/<int:pk>/<int:file_index>/', views.remove_file, name='remove_file'),
    path('contacts-and-channels/', views.get_contacts_and_channels, name='contacts_and_channels'),
    path('update-setting/', views.update_auto_send_setting, name='update_auto_send_setting'),
    path('logout/', views.logout_view, name='logout'),
]

urlpatterns += static('/storage/', document_root=os.path.join(settings.BASE_DIR, 'storage'))