from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import transaction
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.storage import default_storage
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Min, Max, When, Case, F, DecimalField
from .decorators import non_superuser_required


import json
import os

from decimal import Decimal

from .models import Product, Category, Brand, History
from .forms import AccountUpdateForm, RegistrationForm

User = get_user_model()
def validate_images(images):

    if len(images) > 3:
        return 'Chỉ được upload tối đa 3 hình.'

    allowed_extensions = [
        '.jpg',
        '.jpeg',
        '.png',
        '.gif',
        '.webp'
    ]

    for image in images:

        extension = os.path.splitext(
            image.name
        )[1].lower()

        if extension not in allowed_extensions:
            return 'File upload phải là hình ảnh.'

        if image.size > 1024 * 1024:
            return 'Mỗi hình phải có dung lượng nhỏ hơn 1MB.'

    return None


def save_images(images):

    image_filenames = []

    for image in images:

        filename = default_storage.save(
            'product_images/' + image.name,
            image
        )

        image_filenames.append(filename)

    return image_filenames


def get_product_images(product):

    try:

        image_filenames = json.loads(
            product.images or '[]'
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        image_filenames = []


    if not isinstance(
        image_filenames,
        list
    ):
        return []


    image_urls = []


    for image in image_filenames:

        if not image:
            continue

        try:

            image_url = default_storage.url(
                image
            )

            image_urls.append(
                image_url
            )

        except Exception:

            continue


    return image_urls


def get_cart(request):

    cart = request.session.get(
        'cart',
        {}
    )

    if not isinstance(
        cart,
        dict
    ):
        cart = {}

    return cart


def get_cart_count(cart):

    return sum(
        int(quantity)
        for quantity in cart.values()
    )


def register_view(request):

    if request.method == 'POST':

        form = RegistrationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            form.save()

            return redirect(
                'users:login'
            )

    else:

        form = RegistrationForm()


    return render(
        request,
        'users/register.html',
        {
            'form': form
        }
    )


def login_view(request):

    if request.method == 'POST':

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            user = form.get_user()

            login(
                request,
                user
            )

            return redirect(
                '/users/'
            )

    else:

        form = AuthenticationForm()


    return render(
        request,
        'users/login.html',
        {
            'form': form
        }
    )


def logout_view(request):

    logout(request)

    return redirect(
        'users:login'
    )


@non_superuser_required
def account_update(request):

    user = request.user


    if request.method == 'POST':

        form = AccountUpdateForm(
            request.POST,
            request.FILES,
            instance=user
        )


        if form.is_valid():

            user = form.save(
                commit=False
            )


            password1 = form.cleaned_data.get(
                'password1'
            )


            if password1:

                user.set_password(
                    password1
                )


            user.save()


            if password1:

                login(
                    request,
                    user
                )


            return redirect(
                'users:account:update'
            )

    else:

        form = AccountUpdateForm(
            instance=user
        )


    return render(
        request,
        'users/account/update.html',
        {
            'form': form
        }
    )


@non_superuser_required
def my_product(request):

    products = Product.objects.filter(
        user=request.user
    ).order_by(
        '-id'
    )


    product_list = []


    for product in products:

        image_filenames = []

        if product.images:

            try:

                image_filenames = json.loads(
                    product.images
                )

            except (
                json.JSONDecodeError,
                TypeError
            ):

                image_filenames = []


        first_image = None


        if image_filenames:

            try:

                first_image = default_storage.url(
                    image_filenames[0]
                )

            except Exception:

                first_image = None


        product_list.append({

            'id':
                product.id,

            'name':
                product.name,

            'price':
                product.price,

            'image':
                first_image,

        })


    cart = get_cart(
        request
    )


    return render(
        request,
        'users/account/my-product.html',
        {
            'products':
                product_list,

            'cart_count':
                get_cart_count(
                    cart
                ),
        }
    )


@non_superuser_required
def add_product(request):

    categories = Category.objects.all()

    brands = Brand.objects.all()

    error = None


    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()


        price = request.POST.get(
            'price'
        )


        category_id = request.POST.get(
            'category'
        )


        brand_id = request.POST.get(
            'brand'
        )


        status = request.POST.get(
            'status',
            '0'
        )


        sale = request.POST.get(
            'sale',
            '0'
        )


        company = request.POST.get(
            'company',
            ''
        )


        detail = request.POST.get(
            'detail',
            ''
        )


        images = request.FILES.getlist(
            'images'
        )


        error = validate_images(
            images
        )


        if not name:

            error = (
                'Vui lòng nhập tên sản phẩm.'
            )


        elif not price:

            error = (
                'Vui lòng nhập giá sản phẩm.'
            )


        elif not category_id:

            error = (
                'Vui lòng chọn category.'
            )


        elif not brand_id:

            error = (
                'Vui lòng chọn brand.'
            )


        if not error:

            status = int(
                status
            )


            if status == 0:

                sale = 0

            elif not sale:

                sale = 0


            image_filenames = save_images(
                images
            )


            Product.objects.create(

                user=request.user,

                name=name,

                price=price,

                category_id=category_id,

                brand_id=brand_id,

                status=status,

                sale=sale,

                company=company,

                images=json.dumps(
                    image_filenames
                ),

                detail=detail

            )


            return redirect(
                'users:my_product'
            )


    cart = get_cart(
        request
    )


    return render(
        request,
        'users/account/add-product.html',
        {
            'categories':
                categories,

            'brands':
                brands,

            'error':
                error,

            'cart_count':
                get_cart_count(
                    cart
                ),
        }
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


    try:

        old_images = json.loads(
            product.images or '[]'
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        old_images = []


    error = None


    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()


        price = request.POST.get(
            'price'
        )


        category_id = request.POST.get(
            'category'
        )


        brand_id = request.POST.get(
            'brand'
        )


        status = request.POST.get(
            'status',
            '0'
        )


        sale = request.POST.get(
            'sale',
            '0'
        )


        company = request.POST.get(
            'company',
            ''
        )


        detail = request.POST.get(
            'detail',
            ''
        )


        delete_images = request.POST.getlist(
            'delete_images'
        )


        new_images = request.FILES.getlist(
            'images'
        )


        remaining_images = []


        for image in old_images:

            if image not in delete_images:

                remaining_images.append(
                    image
                )


        total_images = (
            len(remaining_images)
            +
            len(new_images)
        )


        if total_images > 3:

            error = (
                'Tổng số hình sau khi cập nhật '
                'không được vượt quá 3 hình.'
            )


        if not error:

            error = validate_images(
                new_images
            )


        if not name:

            error = (
                'Vui lòng nhập tên sản phẩm.'
            )


        elif not price:

            error = (
                'Vui lòng nhập giá sản phẩm.'
            )


        elif not category_id:

            error = (
                'Vui lòng chọn category.'
            )


        elif not brand_id:

            error = (
                'Vui lòng chọn brand.'
            )


        if not error:

            new_image_filenames = save_images(
                new_images
            )


            final_images = (
                remaining_images
                +
                new_image_filenames
            )


            for image in delete_images:

                if image in old_images:

                    if default_storage.exists(
                        image
                    ):

                        default_storage.delete(
                            image
                        )


            product.name = name

            product.price = price

            product.category_id = (
                category_id
            )

            product.brand_id = (
                brand_id
            )

            product.status = int(
                status
            )


            if int(status) == 0:

                product.sale = 0

            else:

                product.sale = (
                    sale or 0
                )


            product.company = company

            product.detail = detail


            product.images = json.dumps(
                final_images
            )


            product.save()


            return redirect(
                'users:my_product'
            )


    old_image_data = []


    for image in old_images:

        old_image_data.append({

            'name':
                image,

            'url':
                default_storage.url(
                    image
                )

        })


    cart = get_cart(
        request
    )


    return render(
        request,
        'users/account/edit-product.html',
        {
            'product':
                product,

            'categories':
                categories,

            'brands':
                brands,

            'old_images':
                old_images,

            'old_image_data':
                old_image_data,

            'error':
                error,

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


    try:

        images = json.loads(
            product.images or '[]'
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        images = []


    for image in images:

        if default_storage.exists(
            image
        ):

            default_storage.delete(
                image
            )


    product.delete()


    return redirect(
        'users:my_product'
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
        product.image_list = get_product_images(product)


    price_data = Product.objects.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )

    min_price = Decimal('0')
    max_price = price_data['max_price'] or Decimal('1000')


    cart = get_cart(request)


    return render(
        request,
        'home.html',
        {
            'products': products,

            'min_price': min_price,
            'max_price': max_price,

            'cart_count': get_cart_count(cart),
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
        get_product_images(
            product
        )
    )


    cart = get_cart(
        request
    )


    return render(
        request,
        'product-details.html',
        {
            'product':
                product,

            'cart_count':
                get_cart_count(
                    cart
                ),
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


        cart = get_cart(
            request
        )


        if product_id in cart:

            cart[product_id] = (
                int(
                    cart[product_id]
                )
                + 1
            )

        else:

            cart[product_id] = 1


        request.session[
            'cart'
        ] = cart


        request.session.modified = True


        return JsonResponse({

            'success':
                True,

            'message':
                'Product added to cart',

            'product_id':
                product.id,

            'product_name':
                product.name,

            'cart_count':
                get_cart_count(
                    cart
                ),

        })


    except Product.DoesNotExist:

        return JsonResponse(
            {
                'success':
                    False,

                'message':
                    'Product not found'
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
                'success':
                    False,

                'message':
                    str(e)
            },
            status=400
        )


def cart_view(request):

    cart = get_cart(
        request
    )


    product_ids = list(
        cart.keys()
    )


    products = (
        Product.objects
        .filter(
            id__in=product_ids
        )
        .select_related(
            'brand',
            'category'
        )
    )


    cart_items = []

    cart_total = Decimal(
        '0.00'
    )


    for product in products:

        quantity = int(
            cart.get(
                str(product.id),
                0
            )
        )


        if quantity <= 0:

            continue


        images = get_product_images(
            product
        )


        if (
            product.status == 1
            and
            product.sale > 0
        ):

            current_price = (
                product.sale
            )

        else:

            current_price = (
                product.price
            )


        item_total = (
            current_price
            *
            quantity
        )


        cart_total += item_total


        cart_items.append({

            'product':
                product,

            'quantity':
                quantity,

            'price':
                current_price,

            'total':
                item_total,

            'image':
                images[0]
                if images
                else '',

        })


    return render(
        request,
        'cart.html',
        {
            'cart_items':
                cart_items,

            'cart_total':
                cart_total,

            'cart_count':
                get_cart_count(
                    cart
                ),
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


        cart = get_cart(
            request
        )


        if product_id not in cart:

            return JsonResponse(
                {
                    'success':
                        False,

                    'message':
                        'Product is not in cart'
                },
                status=400
            )


        if action == 'plus':

            cart[product_id] = (
                int(
                    cart[product_id]
                )
                + 1
            )


        elif action == 'minus':

            cart[product_id] = (
                int(
                    cart[product_id]
                )
                - 1
            )


            if cart[product_id] <= 0:

                del cart[
                    product_id
                ]


        else:

            return JsonResponse(
                {
                    'success':
                        False,

                    'message':
                        'Invalid action'
                },
                status=400
            )


        request.session[
            'cart'
        ] = cart

        request.session.modified = True


        quantity = int(
            cart.get(
                product_id,
                0
            )
        )


        if (
            product.status == 1
            and
            product.sale > 0
        ):

            current_price = (
                product.sale
            )

        else:

            current_price = (
                product.price
            )


        item_total = (
            current_price
            *
            quantity
        )


        cart_total = Decimal(
            '0.00'
        )


        products = Product.objects.filter(
            id__in=cart.keys()
        )


        for p in products:

            qty = int(
                cart.get(
                    str(p.id),
                    0
                )
            )


            if (
                p.status == 1
                and
                p.sale > 0
            ):

                price = p.sale

            else:

                price = p.price


            cart_total += (
                price
                *
                qty
            )


        return JsonResponse({

            'success':
                True,

            'quantity':
                quantity,

            'item_total':
                f'{item_total:.2f}',

            'cart_total':
                f'{cart_total:.2f}',

            'cart_count':
                get_cart_count(
                    cart
                ),

            'removed':
                quantity == 0,

        })


    except Product.DoesNotExist:

        return JsonResponse(
            {
                'success':
                    False,

                'message':
                    'Product not found'
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
                'success':
                    False,

                'message':
                    str(e)
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


        cart = get_cart(
            request
        )


        if product_id in cart:

            del cart[
                product_id
            ]


        request.session[
            'cart'
        ] = cart

        request.session.modified = True


        cart_total = Decimal(
            '0.00'
        )


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


            if (
                product.status == 1
                and
                product.sale > 0
            ):

                price = (
                    product.sale
                )

            else:

                price = (
                    product.price
                )


            cart_total += (
                price
                *
                quantity
            )


        return JsonResponse({

            'success':
                True,

            'cart_count':
                get_cart_count(
                    cart
                ),

            'cart_total':
                f'{cart_total:.2f}',

        })


    except (
        json.JSONDecodeError,
        TypeError,
        ValueError
    ) as e:

        return JsonResponse(
            {
                'success':
                    False,

                'message':
                    str(e)
            },
            status=400
        )

def get_product_price(product):

    if (
        product.status == 1
        and product.sale > 0
    ):
        return product.sale

    return product.price

def checkout(request):

    cart = get_cart(
        request
    )

    product_ids = list(
        cart.keys()
    )

    products = (
        Product.objects
        .filter(
            id__in=product_ids
        )
        .select_related(
            'brand',
            'category'
        )
    )

    checkout_items = []

    total = Decimal(
        '0.00'
    )


    for product in products:

        quantity = int(
            cart.get(
                str(product.id),
                0
            )
        )

        if quantity <= 0:
            continue


        price = get_product_price(
            product
        )


        item_total = (
            price * quantity
        )


        total += item_total


        images = get_product_images(
            product
        )


        checkout_items.append({
            'product': product,
            'quantity': quantity,
            'price': price,
            'total': item_total,
            'image': (
                images[0]
                if images
                else ''
            ),
        })


    if request.method == 'POST':

        if not checkout_items:

            messages.error(
                request,
                'Giỏ hàng đang trống.'
            )

            return redirect(
                'users:cart'
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

            return render(
                request,
                'checkout.html',
                {
                    'checkout_items':
                        checkout_items,

                    'total':
                        total,

                    'cart_count':
                        get_cart_count(cart),
                }
            )


        if not email:

            messages.error(
                request,
                'Vui lòng nhập email.'
            )

            return render(
                request,
                'checkout.html',
                {
                    'checkout_items':
                        checkout_items,

                    'total':
                        total,

                    'cart_count':
                        get_cart_count(cart),
                }
            )


        if not phone:

            messages.error(
                request,
                'Vui lòng nhập số điện thoại.'
            )

            return render(
                request,
                'checkout.html',
                {
                    'checkout_items':
                        checkout_items,

                    'total':
                        total,

                    'cart_count':
                        get_cart_count(cart),
                }
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


            confirm_password = (
                request.POST.get(
                    'confirm_password',
                    ''
                )
            )


            if not username:

                messages.error(
                    request,
                    'Vui lòng nhập username.'
                )

                return render(
                    request,
                    'checkout.html',
                    {
                        'checkout_items':
                            checkout_items,

                        'total':
                            total,

                        'cart_count':
                            get_cart_count(cart),
                    }
                )


            if not password:

                messages.error(
                    request,
                    'Vui lòng nhập password.'
                )

                return render(
                    request,
                    'checkout.html',
                    {
                        'checkout_items':
                            checkout_items,

                        'total':
                            total,

                        'cart_count':
                            get_cart_count(cart),
                    }
                )


            if (
                password
                !=
                confirm_password
            ):

                messages.error(
                    request,
                    'Password không khớp.'
                )

                return render(
                    request,
                    'checkout.html',
                    {
                        'checkout_items':
                            checkout_items,

                        'total':
                            total,

                        'cart_count':
                            get_cart_count(cart),
                    }
                )


            if User.objects.filter(
                username=username
            ).exists():

                messages.error(
                    request,
                    'Username đã tồn tại.'
                )

                return render(
                    request,
                    'checkout.html',
                    {
                        'checkout_items':
                            checkout_items,

                        'total':
                            total,

                        'cart_count':
                            get_cart_count(cart),
                    }
                )


            if User.objects.filter(
                email=email
            ).exists():

                messages.error(
                    request,
                    'Email đã tồn tại. Hãy đăng nhập.'
                )

                return render(
                    request,
                    'checkout.html',
                    {
                        'checkout_items':
                            checkout_items,

                        'total':
                            total,

                        'cart_count':
                            get_cart_count(cart),
                    }
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
                        'history':
                            history,

                        'user':
                            user,

                        'items':
                            checkout_items,

                        'total':
                            total,
                    }
                )


                email_text = strip_tags(
                    email_html
                )


                email_message = (
                    EmailMultiAlternatives(
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

            return render(
                request,
                'checkout.html',
                {
                    'checkout_items':
                        checkout_items,

                    'total':
                        total,

                    'cart_count':
                        get_cart_count(cart),
                }
            )



        request.session[
            'cart'
        ] = {}

        request.session.modified = True


        messages.success(
            request,
            'Đặt hàng thành công. '
            'Thông tin đơn hàng đã được gửi qua email.'
        )


        return redirect(
            'users:checkout'
        )


    return render(
        request,
        'checkout.html',
        {
            'checkout_items':
                checkout_items,

            'total':
                total,

            'cart_count':
                get_cart_count(cart),
        }
    )

def search_product(request):
    keyword = request.GET.get('keyword', '').strip()
    products = Product.objects.none()
    if keyword:
        products = Product.objects.filter(name__icontains=keyword)
    context = {
        'products' : products,
        'keyword' : keyword,
    }
    return render(request, 'search.html', context)

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
            get_product_images(
                product
            )
        )


    params = request.GET.copy()

    if 'page' in params:

        params.pop('page')


    query_string = params.urlencode()


    cart = get_cart(
        request
    )


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
            'page_obj':
                page_obj,

            'categories':
                categories,

            'brands':
                brands,

            'status_choices':
                status_choices,

            'name':
                name,

            'price_range':
                price_range,

            'category_id':
                category_id,

            'brand_id':
                brand_id,

            'status':
                status,

            'query_string':
                query_string,

            'cart_count':
                get_cart_count(
                    cart
                ),
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
        max_price=Max('effective_price')
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