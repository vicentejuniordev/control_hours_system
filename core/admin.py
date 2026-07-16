from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Estagiario, Registro


class EstagiarioInline(admin.StackedInline):
    model = Estagiario
    fk_name = 'user'
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [EstagiarioInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Estagiario)
class EstagiarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'curso', 'instituicao', 'supervisor', 'carga_total', 'inicio', 'fim')
    list_filter = ('supervisor', 'instituicao')
    search_fields = ('nome', 'curso', 'instituicao')
    autocomplete_fields = ('supervisor', 'user')


@admin.register(Registro)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ('estagiario', 'tipo', 'data', 'horas', 'status', 'entrada', 'saida')
    list_filter = ('tipo', 'status', 'data')
    search_fields = ('estagiario__nome', 'descricao')
    date_hierarchy = 'data'
