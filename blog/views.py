from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator

from .models import Blog


def blog_list(request):

    blogs = Blog.objects.all().order_by('-created_at')

    paginator = Paginator(blogs, 3)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'blog/blog.html',
        {
            'page_obj': page_obj
        }
    )


def blog_detail(request, blog_id):
    blog = get_object_or_404(
        Blog,
        id=blog_id
    )

    previous_blog = Blog.objects.filter(
        id__gt=blog.id
    ).order_by('id').first()

    next_blog = Blog.objects.filter(
        id__lt=blog.id
    ).order_by('-id').first()

    return render(
        request,
        'blog/blog-detail.html',
        {
            'blog': blog,
            'previous_blog': previous_blog,
            'next_blog': next_blog,
        }
    )