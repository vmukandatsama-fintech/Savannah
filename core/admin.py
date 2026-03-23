from django.contrib import admin
from .models import Departments, Roles, UserDepartmentRoles, Users, RoleFeature


@admin.register(Departments)
class DepartmentsAdmin(admin.ModelAdmin):
    list_display = ("departmentcode", "name", "departmentid", "isactive", "authrequired")
    search_fields = ("departmentcode", "name")
    list_filter = ("isactive", "authrequired")
    ordering = ("departmentcode",)


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "userid", "isactive")
    search_fields = ("email", "name")
    list_filter = ("isactive",)
    ordering = ("name", "email")


@admin.register(Roles)
class RolesAdmin(admin.ModelAdmin):
    list_display = ("roleid", "name", "description")
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(UserDepartmentRoles)
class UserDepartmentRolesAdmin(admin.ModelAdmin):
    list_display = (
        "mapid",
        "useremail",
        "departmentcode",
        "departmentname",
        "roleid",
        "rolename",
    )
    search_fields = (
        "useremail",
        "departmentcode__departmentcode",
        "departmentcode__name",
        "departmentname",
        "rolename",
    )
    list_select_related = ("departmentcode", "roleid")


@admin.register(RoleFeature)
class RoleFeatureAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "dashboard",
        "create_request",
        "my_requests",
        "approvals",
        "collections",
        "reports",
        "admin",
    )
    list_select_related = ("role",)
    search_fields = ("role__name",)
    list_editable = (
        "dashboard",
        "create_request",
        "my_requests",
        "approvals",
        "collections",
        "reports",
        "admin",
    )
