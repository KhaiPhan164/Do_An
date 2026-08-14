from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
import json
import os

from .models import Product, Category, Brand

from .forms import AccountUpdateForm, RegistrationForm


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

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            form.save()
            return redirect('users:login')

    else:
        form = RegistrationForm()

    return render(
        request,
        'users/register.html',
        {'form': form}
    )


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            return redirect('blog:blog_list')

    else:
        form = AuthenticationForm()

    return render(
        request,
        'users/login.html',
        {'form': form}
    )


def logout_view(request):
    logout(request)
    return redirect('users:login')

@login_required
def account_update(request):
    user = request.user
    if request.method == 'POST':
        form = AccountUpdateForm(
            request.POST,
            request.FILES,
            instance=user
        )

        if form.is_valid():
            user = form.save(commit=False)
            password1 = form.cleaned_data.get('password1')
            if password1:
                user.set_password(password1)
            user.save()
            if password1:
                login(request, user)
            
            return redirect('users:account:update')
    else: 
        form = AccountUpdateForm(instance=user)
    return render(request, 'users/account/update.html', {'form': form})



@login_required
def my_product(request):

    products = Product.objects.filter(
        user=request.user
    ).order_by('-id')

    product_list = []

    for product in products:

        image_filenames = []

        if product.images:

            try:
                image_filenames = json.loads(
                    product.images
                )
            except:
                image_filenames = []

        first_image = None

        if image_filenames:
            first_image = image_filenames[0]

        product_list.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'image': first_image,
        })

    return render(
        request,
        'users/account/my-product.html',
        {
            'products': product_list
        }
    )
@login_required
def add_product(request):

    categories = Category.objects.all()
    brands = Brand.objects.all()

    error = None

    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()

        price = request.POST.get('price')

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

        error = validate_images(images)

        if not name:
            error = 'Vui lòng nhập tên sản phẩm.'

        elif not price:
            error = 'Vui lòng nhập giá sản phẩm.'

        elif not category_id:
            error = 'Vui lòng chọn category.'

        elif not brand_id:
            error = 'Vui lòng chọn brand.'


        if not error:

            status = int(status)

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


    return render(
        request,
        'users/account/add-product.html',
        {
            'categories': categories,
            'brands': brands,
            'error': error,
        }
    )


@login_required
def edit_product(request, product_id):

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
    except:
        old_images = []


    error = None


    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()

        price = request.POST.get('price')

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
                remaining_images.append(image)


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

                    if default_storage.exists(image):

                        default_storage.delete(
                            image
                        )


            product.name = name

            product.price = price

            product.category_id = category_id

            product.brand_id = brand_id

            product.status = int(status)

            if int(status) == 0:
                product.sale = 0
            else:
                product.sale = sale or 0

            product.company = company

            product.detail = detail

            product.images = json.dumps(
                final_images
            )

            product.save()


            return redirect(
                'users:my_product'
            )


    return render(
        request,
        'users/account/edit-product.html',
        {
            'product': product,
            'categories': categories,
            'brands': brands,
            'old_images': old_images,
            'error': error,
        }
    )
@login_required
def delete_product(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        user=request.user
    )

    try:
        images = json.loads(
            product.images or '[]'
        )
    except:
        images = []


    for image in images:

        if default_storage.exists(image):
            default_storage.delete(image)


    product.delete()

    return redirect(
        'users:my_product'
    )