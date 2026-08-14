from django.urls import path

from . import views


app_name = 'blog'


urlpatterns = [

    path(
        '',
        views.blog_list,
        name='blog_list'
    ),

    path(
        '<int:blog_id>/',
        views.blog_detail,
        name='blog_detail'
    ),

    path(
        '<int:blog_id>/rate/',
        views.rate_blog,
        name='rate_blog'
    ),

    path(
            '<int:blog_id>/comment/',
            views.comment_blog,
            name='comment_blog'
        ),

]