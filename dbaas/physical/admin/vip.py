# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.contrib import admin


class VipAdmin(admin.ModelAdmin):
    search_fields = ("identifier", "infra")
    list_display = ("identifier", "infra", "original_vip")
    save_on_top = True 
