import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings')
django.setup()

from blog.models import Plan
plans = Plan.objects.all().order_by('id')
for i, plan in enumerate(plans):
    print(f"Setting plan {plan.id} to order {i}")
    plan.order = i
    plan.save()
print("All plans successfully initialized!")
