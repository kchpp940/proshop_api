from django.contrib import admin
from .models import *


class AdminActionAuditAdmin(admin.ModelAdmin):
    list_display = ('_id', 'operator_email', 'resource_type', 'resource_id',
                    'action_type', 'status', 'ip_address', 'created_at')
    list_filter = ('resource_type', 'action_type', 'status', 'created_at')
    search_fields = ('operator_email', 'resource_id', 'ip_address', 'error_message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


admin.site.register(Product)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Review)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)
admin.site.register(AdminActionAudit, AdminActionAuditAdmin)
