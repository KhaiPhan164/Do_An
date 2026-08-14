from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Avg

from .models import Blog, Rates, Comments


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

    average_rate = Rates.objects.filter(
        blog=blog
    ).aggregate(
        avg=Avg('rate')
    )['avg']

    if average_rate is None:
        average_rate = 0
    else:
        average_rate = round(average_rate, 1)

    comments = Comments.objects.filter(
        blog_id=blog_id,
        parent__isnull=True
    ).select_related('user').order_by('-time')

    context = {
        'blog': blog,
        'comments': comments,
    }

    return render(
        request,
        'blog/blog-detail.html',
        {
            'blog': blog,
            'previous_blog': previous_blog,
            'next_blog': next_blog,
            'average_rate': average_rate,
            'comments': comments
        }
    )


def rate_blog(request, blog_id):

    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Invalid request method'
        })

    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Bạn cần đăng nhập để đánh giá.'
        })

    rate = request.POST.get('rate')

    try:
        rate = int(rate)

        if rate < 1 or rate > 5:
            return JsonResponse({
                'success': False,
                'error': 'Rate must be between 1 and 5'
            })

    except (TypeError, ValueError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid rate'
        })

    blog = get_object_or_404(
        Blog,
        id=blog_id
    )

    rating, created = Rates.objects.update_or_create(
        blog=blog,
        author=request.user,
        defaults={
            'rate': rate
        }
    )

    average_rate = Rates.objects.filter(
        blog=blog
    ).aggregate(
        avg=Avg('rate')
    )['avg']

    if average_rate is None:
        average_rate = 0

    average_rate = round(average_rate, 1)

    return JsonResponse({
        'success': True,
        'rate': rating.rate,
        'average_rate': average_rate,
    })


def comment_blog(request, blog_id):
    if request.method == 'POST':

        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'User not authenticated'
            })

        comment = request.POST.get('comment')

        if not comment:
            return JsonResponse({
                'success': False,
                'error': 'Comment cannot be empty'
            })

        try:
            new_comment = Comments.objects.create(
                blog_id=blog_id,
                user=request.user,
                comment=comment,
                level=0
            )

            return JsonResponse({
                'success': True,
                'data': {
                    'id': new_comment.id,
                    'blog_id': new_comment.blog_id,
                    'comment': new_comment.comment,
                    'user_id': new_comment.user.id,
                    'username': new_comment.user.username,
                    'level': new_comment.level,
                    'time': new_comment.time,
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })