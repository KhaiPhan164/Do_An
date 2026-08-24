from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Avg
from django.utils.timezone import localtime
from .models import Blog, Rates, Comments


def blog_list(request):
    blogs = Blog.objects.all().order_by('-created_at')

    paginator = Paginator(blogs, 3)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'blog.html',
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
        average_rate = round(
            average_rate,
            1
        )


    user_rate = 0

    if request.user.is_authenticated:

        user_rating = Rates.objects.filter(
            blog=blog,
            author=request.user
        ).first()

        if user_rating:
            user_rate = user_rating.rate


    comments = Comments.objects.filter(
        blog=blog,
        parent__isnull=True
    ).select_related(
        'user'
    ).prefetch_related(
        'replies__user'
    ).order_by('-time')


    return render(
        request,
        'blog-detail.html',
        {
            'blog': blog,
            'previous_blog': previous_blog,
            'next_blog': next_blog,
            'average_rate': average_rate,
            'user_rate': user_rate,
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

    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Invalid request method'
        })

    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'User not authenticated'
        })

    blog = get_object_or_404(
        Blog,
        id=blog_id
    )

    comment = request.POST.get(
        'comment',
        ''
    ).strip()

    parent_id = request.POST.get(
        'parent_id'
    )

    if not comment:
        return JsonResponse({
            'success': False,
            'error': 'Comment cannot be empty'
        })


    parent = None

    if parent_id:

        parent = get_object_or_404(
            Comments,
            id=parent_id,
            blog=blog,
            parent__isnull=True
        )


    try:

        new_comment = Comments.objects.create(
            blog=blog,
            user=request.user,
            comment=comment,
            parent=parent,
            level=1 if parent else 0
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

                'parent_id': new_comment.parent_id,

                'time': localtime(
                     new_comment.time
                    ).strftime(
                        '%d/%m/%Y %H:%M'
                    )

            }
        })


    except Exception as e:

        return JsonResponse({
            'success': False,
            'error': str(e)
        })