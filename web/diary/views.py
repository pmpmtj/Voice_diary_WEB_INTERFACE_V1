from django.shortcuts import render
from django.core.paginator import Paginator

from .models import IngestItem


def home(request):
    items = IngestItem.objects.filter(is_deleted=False).order_by("-occurred_at")
    paginator = Paginator(items, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "diary/home.html", {"page_obj": page_obj})


