from decimal import Decimal, InvalidOperation
import json
import os
from PIL import Image
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, DecimalField, F, Max, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST

from users.decorators import non_superuser_required
from users.models import Product, Category, Brand, History


User = get_user_model()


def validate_images(
    images,
    required=True
):

    if required and not images:
        return 'Phải chọn ít nhất một hình.'

    if len(images) > 3:
        return 'Chỉ được upload tối đa 3 hình.'

    allowed_extensions = [
        '.jpg',
        '.jpeg',
        '.png',
        '.gif',
        '.webp',
    ]

    max_size = 2 * 1024 * 1024

    for image in images:

        extension = os.path.splitext(
            image.name
        )[1].lower()

        if extension not in allowed_extensions:
            return 'File upload phải là hình ảnh.'

        if image.size > max_size:
            return 'Mỗi hình phải có dung lượng nhỏ hơn 2MB.'

    return None


def save_images(images):

    saved_filenames = []

    save_folder = os.path.join(
        settings.MEDIA_ROOT,
        'products'
    )

    os.makedirs(
        save_folder,
        exist_ok=True
    )


    for image in images:

        filename = image.name.replace(
            ' ',
            '_'
        )

        base, ext = os.path.splitext(
            filename
        )

        ext = ext.lower()


        original_name = (
            f'{base}{ext}'
        )

        original_path = os.path.join(
            save_folder,
            original_name
        )


        with open(
            original_path,
            'wb+'
        ) as destination:

            for chunk in image.chunks():
                destination.write(
                    chunk
                )


        saved_filenames.append(
            f'products/{original_name}'
        )


        img = Image.open(
            original_path
        )


        for size in [
            100,
            200
        ]:

            img_copy = img.copy()

            img_copy.thumbnail(
                (
                    size,
                    size
                )
            )

            resized_name = (
                f'{size}_{base}{ext}'
            )

            resized_path = os.path.join(
                save_folder,
                resized_name
            )

            img_copy.save(
                resized_path
            )


    return saved_filenames


def get_image_filenames(product):
    try:
        image_filenames = json.loads(
            product.images or '[]'
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):
        return []

    if not isinstance(image_filenames, list):
        return []

    return image_filenames


def get_product_images(product):
    image_urls = []

    for image in get_image_filenames(product):
        if not image:
            continue

        try:
            image_urls.append(
                default_storage.url(image)
            )

        except Exception:
            continue

    return image_urls


def get_product_price(product):
    if (
        product.status == 1
        and product.sale > 0
    ):
        return product.sale

    return product.price


def get_cart(request):
    cart = request.session.get(
        'cart',
        {}
    )

    if not isinstance(cart, dict):
        cart = {}

    return cart


def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def get_cart_count(cart):
    return sum(
        int(quantity)
        for quantity in cart.values()
    )


def get_cart_total(cart):
    total = Decimal('0.00')

    products = Product.objects.filter(
        id__in=cart.keys()
    )

    for product in products:
        quantity = int(
            cart.get(
                str(product.id),
                0
            )
        )

        total += (
            get_product_price(product)
            * quantity
        )

    return total


def build_cart_items(cart):
    products = (
        Product.objects
        .filter(
            id__in=cart.keys()
        )
        .select_related(
            'brand',
            'category'
        )
    )

    items = []
    total = Decimal('0.00')

    for product in products:
        quantity = int(
            cart.get(
                str(product.id),
                0
            )
        )

        if quantity <= 0:
            continue

        price = get_product_price(product)
        item_total = price * quantity

        images = get_product_images(product)

        total += item_total

        items.append({
            'product': product,
            'quantity': quantity,
            'price': price,
            'total': item_total,
            'image': images[0] if images else '',
        })

    return items, total


def render_checkout(
    request,
    checkout_items,
    total,
    cart
):
    return render(
        request,
        'checkout.html',
        {
            'checkout_items': checkout_items,
            'total': total,
            'cart_count': get_cart_count(cart),
        }
    )


@non_superuser_required
def my_product(request):
    products = (
        Product.objects
        .filter(
            user=request.user
        )
        .order_by('-id')
    )

    product_list = []

    for product in products:
        images = get_product_images(product)

        product_list.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'image': (
                images[0]
                if images
                else None
            ),
        })

    cart = get_cart(request)

    return render(
        request,
        'my-product.html',
        {
            'products': product_list,
            'cart_count': get_cart_count(cart),
        }
    )


@non_superuser_required
def add_product(request):

    categories = Category.objects.all()
    brands = Brand.objects.all()

    cart = get_cart(request)

    return render(
        request,
        'add-product.html',
        {
            'categories': categories,
            'brands': brands,
            'cart_count': get_cart_count(cart),
        }
    )

@non_superuser_required
@require_POST
def add_product_ajax(request):

    data = get_product_form_data(
        request
    )

    images = request.FILES.getlist(
        'images'
    )

    errors = validate_product_data(
        data
    )

    image_error = validate_images(
        images,
        required=True
    )

    if image_error:

        errors['images'] = (
            image_error
        )


    if errors:

        return JsonResponse(
            {
                'status': 'error',
                'errors': errors,
            },
            status=400
        )


    image_filenames = []


    try:

        image_filenames = save_images(
            images
        )


        product = Product(
            user=request.user
        )


        set_product_data(
            product,
            data
        )


        product.images = json.dumps(
            image_filenames
        )


        product.save()


        return JsonResponse(
            {
                'status': 'success',
                'message': (
                    'Thêm sản phẩm thành công.'
                ),
                'product_id': product.id,
            }
        )


    except Exception as e:

        return JsonResponse(
            {
                'status': 'error',

                'errors': {
                    'general': str(e)
                },
            },
            status=500
        )

@non_superuser_required
def edit_product(
    request,
    product_id
):

    product = get_object_or_404(
        Product,
        id=product_id,
        user=request.user
    )


    categories = Category.objects.all()

    brands = Brand.objects.all()


    old_images = get_image_filenames(
        product
    )


    error = None


    if request.method == 'POST':

        data = get_product_form_data(
            request
        )


        errors = validate_product_data(
            data
        )


        delete_images = (
            request.POST.getlist(
                'delete_images'
            )
        )


        delete_images = [
            image
            for image in delete_images
            if image in old_images
        ]


        new_images = (
            request.FILES.getlist(
                'images'
            )
        )


        remaining_images = [
            image
            for image in old_images
            if image not in delete_images
        ]


        total_images = (
            len(remaining_images)
            +
            len(new_images)
        )


        if total_images == 0:

            errors['images'] = (
                'Sản phẩm phải có ít nhất một hình.'
            )


        elif total_images > 3:

            errors['images'] = (
                'Tổng số hình sau khi cập nhật '
                'không được vượt quá 3 hình.'
            )


        else:

            image_error = validate_images(
                new_images,
                required=False
            )


            if image_error:

                errors['images'] = (
                    image_error
                )


        if errors:

            error = next(
                iter(
                    errors.values()
                )
            )


        else:

            new_image_filenames = []


            try:

                new_image_filenames = (
                    save_images(
                        new_images
                    )
                )


                final_images = (
                    remaining_images
                    +
                    new_image_filenames
                )


                set_product_data(
                    product,
                    data
                )


                product.images = json.dumps(
                    final_images
                )


                product.save()


                for image in delete_images:

                    if default_storage.exists(
                        image
                    ):

                        default_storage.delete(
                            image
                        )


                return redirect(
                    'product:my_product'
                )


            except Exception as e:

                error = str(e)


    old_image_data = []


    for image in old_images:

        try:

            image_url = (
                default_storage.url(
                    image
                )
            )

        except Exception:

            image_url = ''


        old_image_data.append(
            {
                'name': image,
                'url': image_url,
            }
        )


    cart = get_cart(
        request
    )


    return render(
        request,
        'edit-product.html',
        {
            'product': product,

            'categories': categories,

            'brands': brands,

            'old_images': old_images,

            'old_image_data':
                old_image_data,

            'error': error,

            'cart_count':
                get_cart_count(
                    cart
                ),
        }
    )

@non_superuser_required
def delete_product(
    request,
    product_id
):
    product = get_object_or_404(
        Product,
        id=product_id,
        user=request.user
    )

    images = get_image_filenames(
        product
    )

    for image in images:
        if default_storage.exists(image):
            default_storage.delete(image)

    product.delete()

    return redirect(
        'product:my_product'
    )


def home(request):
    products = (
        Product.objects
        .select_related(
            'category',
            'brand',
            'user'
        )
        .order_by(
            '-created_at'
        )[:6]
    )

    for product in products:
        product.image_list = (
            get_product_images(product)
        )

    price_data = Product.objects.aggregate(
        max_price=Max('price')
    )

    min_price = Decimal('0')

    max_price = (
        price_data['max_price']
        or Decimal('1000')
    )

    cart = get_cart(request)

    return render(
        request,
        'home.html',
        {
            'products': products,
            'min_price': min_price,
            'max_price': max_price,
            'cart_count': get_cart_count(cart),

            'show_price_range': True,
        }
    )


def product_detail(
    request,
    id
):
    product = get_object_or_404(
        Product.objects.select_related(
            'category',
            'brand',
            'user'
        ),
        id=id
    )

    product.image_list = (
        get_product_images(product)
    )

    cart = get_cart(request)

    return render(
        request,
        'product-details.html',
        {
            'product': product,
            'cart_count': get_cart_count(cart),
        }
    )


@require_POST
def add_to_cart(request):
    try:
        data = json.loads(
            request.body
        )

        product_id = str(
            data.get(
                'product_id'
            )
        )

        product = Product.objects.get(
            id=product_id
        )

        cart = get_cart(request)

        if product_id in cart:
            cart[product_id] = (
                int(cart[product_id])
                + 1
            )

        else:
            cart[product_id] = 1

        save_cart(
            request,
            cart
        )

        return JsonResponse({
            'success': True,
            'message': 'Product added to cart',
            'product_id': product.id,
            'product_name': product.name,
            'cart_count': get_cart_count(cart),
        })

    except Product.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'message': 'Product not found',
            },
            status=404
        )

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError
    ) as e:
        return JsonResponse(
            {
                'success': False,
                'message': str(e),
            },
            status=400
        )


def cart_view(request):
    cart = get_cart(request)

    cart_items, cart_total = (
        build_cart_items(cart)
    )

    return render(
        request,
        'cart.html',
        {
            'cart_items': cart_items,
            'cart_total': cart_total,
            'cart_count': get_cart_count(cart),
        }
    )


@require_POST
def update_cart(request):
    try:
        data = json.loads(
            request.body
        )

        product_id = str(
            data.get(
                'product_id'
            )
        )

        action = data.get(
            'action'
        )

        product = Product.objects.get(
            id=product_id
        )

        cart = get_cart(request)

        if product_id not in cart:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Product is not in cart',
                },
                status=400
            )

        if action == 'plus':
            cart[product_id] = (
                int(cart[product_id])
                + 1
            )

        elif action == 'minus':
            cart[product_id] = (
                int(cart[product_id])
                - 1
            )

            if cart[product_id] <= 0:
                del cart[product_id]

        else:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Invalid action',
                },
                status=400
            )

        save_cart(
            request,
            cart
        )

        quantity = int(
            cart.get(
                product_id,
                0
            )
        )

        current_price = (
            get_product_price(product)
        )

        item_total = (
            current_price
            * quantity
        )

        cart_total = get_cart_total(
            cart
        )

        return JsonResponse({
            'success': True,
            'quantity': quantity,
            'item_total': f'{item_total:.2f}',
            'cart_total': f'{cart_total:.2f}',
            'cart_count': get_cart_count(cart),
            'removed': quantity == 0,
        })

    except Product.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'message': 'Product not found',
            },
            status=404
        )

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError
    ) as e:
        return JsonResponse(
            {
                'success': False,
                'message': str(e),
            },
            status=400
        )


@require_POST
def delete_cart_item(request):
    try:
        data = json.loads(
            request.body
        )

        product_id = str(
            data.get(
                'product_id'
            )
        )

        cart = get_cart(request)

        if product_id in cart:
            del cart[product_id]

        save_cart(
            request,
            cart
        )

        cart_total = get_cart_total(
            cart
        )

        return JsonResponse({
            'success': True,
            'cart_count': get_cart_count(cart),
            'cart_total': f'{cart_total:.2f}',
        })

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError
    ) as e:
        return JsonResponse(
            {
                'success': False,
                'message': str(e),
            },
            status=400
        )


def checkout(request):
    cart = get_cart(request)

    checkout_items, total = (
        build_cart_items(cart)
    )

    if request.method == 'POST':

        if not checkout_items:
            messages.error(
                request,
                'Giỏ hàng đang trống.'
            )

            return redirect(
                'product:cart'
            )

        name = request.POST.get(
            'name',
            ''
        ).strip()

        email = request.POST.get(
            'email',
            ''
        ).strip()

        phone = request.POST.get(
            'phone',
            ''
        ).strip()

        if not name:
            messages.error(
                request,
                'Vui lòng nhập họ tên.'
            )

            return render_checkout(
                request,
                checkout_items,
                total,
                cart
            )

        if not email:
            messages.error(
                request,
                'Vui lòng nhập email.'
            )

            return render_checkout(
                request,
                checkout_items,
                total,
                cart
            )

        if not phone:
            messages.error(
                request,
                'Vui lòng nhập số điện thoại.'
            )

            return render_checkout(
                request,
                checkout_items,
                total,
                cart
            )

        user = request.user

        if not request.user.is_authenticated:
            username = request.POST.get(
                'username',
                ''
            ).strip()

            password = request.POST.get(
                'password',
                ''
            )

            confirm_password = request.POST.get(
                'confirm_password',
                ''
            )

            if not username:
                messages.error(
                    request,
                    'Vui lòng nhập username.'
                )

                return render_checkout(
                    request,
                    checkout_items,
                    total,
                    cart
                )

            if not password:
                messages.error(
                    request,
                    'Vui lòng nhập password.'
                )

                return render_checkout(
                    request,
                    checkout_items,
                    total,
                    cart
                )

            if password != confirm_password:
                messages.error(
                    request,
                    'Password không khớp.'
                )

                return render_checkout(
                    request,
                    checkout_items,
                    total,
                    cart
                )

            if User.objects.filter(
                username=username
            ).exists():
                messages.error(
                    request,
                    'Username đã tồn tại.'
                )

                return render_checkout(
                    request,
                    checkout_items,
                    total,
                    cart
                )

            if User.objects.filter(
                email=email
            ).exists():
                messages.error(
                    request,
                    'Email đã tồn tại. Hãy đăng nhập.'
                )

                return render_checkout(
                    request,
                    checkout_items,
                    total,
                    cart
                )

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            name_parts = name.split(
                ' ',
                1
            )

            user.first_name = (
                name_parts[0]
                if name_parts
                else ''
            )

            if len(name_parts) > 1:
                user.last_name = (
                    name_parts[1]
                )

            user.save()

            login(
                request,
                user
            )

        else:
            user = request.user

            if (
                email
                and user.email != email
            ):
                user.email = email

                user.save(
                    update_fields=[
                        'email'
                    ]
                )

        try:
            with transaction.atomic():
                history = History.objects.create(
                    user=user,
                    email=email,
                    phone=phone,
                    name=name,
                    price=total
                )

                email_html = render_to_string(
                    'emails/order-confirmation.html',
                    {
                        'history': history,
                        'user': user,
                        'items': checkout_items,
                        'total': total,
                    }
                )

                email_text = strip_tags(
                    email_html
                )

                email_message = EmailMultiAlternatives(
                    subject=(
                        'E-Shopper - '
                        f'Order #{history.id}'
                    ),
                    body=email_text,
                    from_email=None,
                    to=[
                        email
                    ],
                )

                email_message.attach_alternative(
                    email_html,
                    'text/html'
                )

                email_message.send(
                    fail_silently=False
                )

        except Exception as e:
            messages.error(
                request,
                'Không thể hoàn tất đơn hàng: '
                + str(e)
            )

            return render_checkout(
                request,
                checkout_items,
                total,
                cart
            )

        save_cart(
            request,
            {}
        )

        messages.success(
            request,
            'Đặt hàng thành công. '
            'Thông tin đơn hàng đã được gửi qua email.'
        )

        return redirect(
            'product:checkout'
        )

    return render_checkout(
        request,
        checkout_items,
        total,
        cart
    )


def search_product(request):
    keyword = request.GET.get(
        'keyword',
        ''
    ).strip()

    products = Product.objects.none()

    if keyword:
        products = Product.objects.filter(
            name__icontains=keyword
        )

    context = {
        'products': products,
        'keyword': keyword,
    }

    return render(
        request,
        'search.html',
        context
    )


def search_advanced(request):
    products = (
        Product.objects
        .select_related(
            'category',
            'brand',
            'user'
        )
        .order_by('-id')
    )

    categories = Category.objects.all()
    brands = Brand.objects.all()

    name = request.GET.get(
        'name',
        ''
    ).strip()

    price_range = request.GET.get(
        'price',
        ''
    )

    category_id = request.GET.get(
        'category',
        ''
    )

    brand_id = request.GET.get(
        'brand',
        ''
    )

    status = request.GET.get(
        'status',
        ''
    )

    if name:
        products = products.filter(
            name__icontains=name
        )

    if price_range:
        try:
            min_price, max_price = (
                price_range.split('-')
            )

            products = products.filter(
                price__range=(
                    Decimal(min_price),
                    Decimal(max_price)
                )
            )

        except (
            ValueError,
            TypeError
        ):
            pass

    if category_id:
        products = products.filter(
            category_id=category_id
        )

    if brand_id:
        products = products.filter(
            brand_id=brand_id
        )

    if status != '':
        products = products.filter(
            status=status
        )

    paginator = Paginator(
        products,
        6
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    for product in page_obj:
        product.image_list = (
            get_product_images(product)
        )

    params = request.GET.copy()

    if 'page' in params:
        params.pop('page')

    query_string = params.urlencode()

    cart = get_cart(request)

    status_choices = (
        Product
        ._meta
        .get_field('status')
        .choices
    )

    return render(
        request,
        'search-advanced.html',
        {
            'page_obj': page_obj,
            'categories': categories,
            'brands': brands,
            'status_choices': status_choices,
            'name': name,
            'price_range': price_range,
            'category_id': category_id,
            'brand_id': brand_id,
            'status': status,
            'query_string': query_string,
            'cart_count': get_cart_count(cart),
        }
    )


def search_price(request):
    products_query = Product.objects.annotate(
        effective_price=Case(
            When(
                status=1,
                sale__gt=0,
                then=F('sale')
            ),
            default=F('price'),
            output_field=DecimalField(
                max_digits=10,
                decimal_places=2
            )
        )
    )

    price_data = products_query.aggregate(
        max_price=Max(
            'effective_price'
        )
    )

    default_min = 0

    default_max = (
        price_data['max_price']
        or 1000
    )

    min_price = request.GET.get(
        'min_price',
        default_min
    )

    max_price = request.GET.get(
        'max_price',
        default_max
    )

    products = (
        products_query
        .filter(
            effective_price__range=(
                min_price,
                max_price
            )
        )
        .order_by('-created_at')
    )

    for product in products:
        product.image_list = (
            get_product_images(product)
        )

    html = render_to_string(
        'product-price-list.html',
        {
            'products': products
        },
        request=request
    )

    return JsonResponse({
        'html': html
    })

def get_product_form_data(request):

    return {
        'name': request.POST.get(
            'name',
            ''
        ).strip(),

        'price': request.POST.get(
            'price',
            ''
        ).strip(),

        'category_id': request.POST.get(
            'category',
            ''
        ),

        'brand_id': request.POST.get(
            'brand',
            ''
        ),

        'status': request.POST.get(
            'status',
            '0'
        ),

        'sale': request.POST.get(
            'sale',
            '0'
        ),

        'company': request.POST.get(
            'company',
            ''
        ).strip(),

        'detail': request.POST.get(
            'detail',
            ''
        ).strip(),
    }

def validate_product_data(data):

    errors = {}


    if not data['name']:

        errors['name'] = (
            'Tên sản phẩm không được để trống.'
        )


    if not data['price']:

        errors['price'] = (
            'Giá không được để trống.'
        )

    else:

        try:

            price = Decimal(
                data['price']
            )

            if (
                not price.is_finite()
                or price < 0
            ):

                errors['price'] = (
                    'Giá phải lớn hơn hoặc bằng 0.'
                )

            else:

                data['price'] = price

        except (
            InvalidOperation,
            ValueError,
            TypeError
        ):

            errors['price'] = (
                'Giá không hợp lệ.'
            )


    if not data['category_id']:

        errors['category'] = (
            'Vui lòng chọn category.'
        )


    if not data['brand_id']:

        errors['brand'] = (
            'Vui lòng chọn brand.'
        )


    try:

        status = int(
            data['status']
        )

        allowed_statuses = {
            choice[0]
            for choice
            in Product
            ._meta
            .get_field('status')
            .choices
        }

        if status not in allowed_statuses:
            raise ValueError

        data['status'] = status

    except (
        ValueError,
        TypeError
    ):

        errors['status'] = (
            'Trạng thái sản phẩm không hợp lệ.'
        )

        data['status'] = 0


    if data['status'] == 0:

        data['sale'] = Decimal(
            '0'
        )

    else:

        try:

            sale = Decimal(
                data['sale'] or '0'
            )

            if (
                not sale.is_finite()
                or sale < 0
            ):

                errors['sale'] = (
                    'Giá sale không hợp lệ.'
                )

            else:

                data['sale'] = sale

        except (
            InvalidOperation,
            ValueError,
            TypeError
        ):

            errors['sale'] = (
                'Giá sale không hợp lệ.'
            )


    return errors

def set_product_data(
    product,
    data
):

    product.name = (
        data['name']
    )

    product.price = (
        data['price']
    )

    product.category_id = (
        data['category_id']
    )

    product.brand_id = (
        data['brand_id']
    )

    product.status = (
        data['status']
    )

    product.sale = (
        data['sale']
    )

    product.company = (
        data['company']
    )

    product.detail = (
        data['detail']
    )