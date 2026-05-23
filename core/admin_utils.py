from functools import lru_cache

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db import connection


@lru_cache(maxsize=1)
def mysql_timezone_supports_date_hierarchy():
    if connection.vendor != 'mysql':
        return True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT CONVERT_TZ(NOW(), 'UTC', 'UTC')")
            return cursor.fetchone()[0] is not None
    except Exception:
        return False


class SafeDateHierarchyChangeList(ChangeList):
    def __init__(
        self,
        request,
        model,
        list_display,
        list_display_links,
        list_filter,
        date_hierarchy,
        search_fields,
        list_select_related,
        list_per_page,
        list_max_show_all,
        list_editable,
        model_admin,
        sortable_by,
        search_help_text,
    ):
        if date_hierarchy and not mysql_timezone_supports_date_hierarchy():
            date_hierarchy = None

        super().__init__(
            request,
            model,
            list_display,
            list_display_links,
            list_filter,
            date_hierarchy,
            search_fields,
            list_select_related,
            list_per_page,
            list_max_show_all,
            list_editable,
            model_admin,
            sortable_by,
            search_help_text,
        )


class SafeDateHierarchyAdmin(admin.ModelAdmin):
    def get_changelist(self, request, **kwargs):
        return SafeDateHierarchyChangeList