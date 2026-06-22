from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.activities.models import Activity
from apps.elder_services.models import ElderServiceTask
from apps.learning.models import LearningContent
from apps.members.models import Member
from apps.merchants.models import Merchant, MerchantProduct


class Command(BaseCommand):
    help = "创建一期 MVP 最小验收数据。"

    def handle(self, *args, **options):
        User = get_user_model()
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"is_backend_manager": True, "is_staff": True, "is_superuser": True},
        )
        admin.is_backend_manager = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("admin123456")
        admin.save()

        member, _ = Member.objects.update_or_create(
            openid="test-member-openid",
            defaults={"nickname": "测试用户", "phone": "13800000000", "role": Member.Role.COURIER, "is_active": True},
        )
        merchant, _ = Merchant.objects.update_or_create(
            openid="test-merchant-openid",
            defaults={"name": "测试商户", "contact_name": "商户联系人", "phone": "13900000000", "address": "测试街道", "is_active": True},
        )
        LearningContent.objects.update_or_create(
            title="街道服务安全学习",
            defaults={"body": "学习内容正文", "points": 5, "required_seconds": 60, "is_active": True},
        )
        Activity.objects.update_or_create(
            title="社区志愿活动",
            defaults={
                "body": "活动正文",
                "location": "社区中心",
                "start_time": timezone.now() + timezone.timedelta(days=1),
                "end_time": timezone.now() + timezone.timedelta(days=1, hours=2),
                "points": 8,
                "status": Activity.Status.PUBLISHED,
            },
        )
        ElderServiceTask.objects.update_or_create(
            title="探访老人服务",
            defaults={"description": "服务描述", "location": "社区", "points": 10, "status": ElderServiceTask.Status.PUBLISHED},
        )
        MerchantProduct.objects.update_or_create(
            merchant=merchant,
            name="爱心兑换商品",
            defaults={"description": "商品说明", "points_required": 20, "is_active": True},
        )

        self.stdout.write(self.style.SUCCESS(f"MVP 验收数据已准备：用户 {member.openid}，商户 {merchant.openid}，后台 admin/admin123456"))
