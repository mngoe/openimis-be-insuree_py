# Register your models here.
from django.contrib import admin
from .models import Insuree
from .models import Gender
from .models import Question
from .models import Option
from .models import InsureeAnswer

admin.site.register(Insuree)
admin.site.register(Gender)
admin.site.register(Question)
admin.site.register(Option)
admin.site.register(InsureeAnswer)