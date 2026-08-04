from django.contrib import admin
from .models import User, country
# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'created_at')
    search_fields = ('username', 'email')
    list_filter = ('created_at',)

@admin.register(country)
class countryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)