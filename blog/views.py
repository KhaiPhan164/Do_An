from django.shortcuts import render
from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField

# Create your views here.
class Blog(models.Model):
    title = models.CharField(max_length=200)
    des = models.TextField()
    content = RichTextUploadingField()
    image = models.ImageField(upload_to='blogs/')
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey('shoppe.User', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title