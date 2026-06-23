from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.activities.models import Activity, ActivityCheckin, ActivitySignup
from apps.elder_services.models import ElderServiceFeedback, ElderServiceTask
from apps.learning.models import LearningContent, LearningRecord
from apps.members.models import Member
from apps.merchants.models import Merchant, MerchantProduct, ProductRedemption
from apps.points.models import PointAccount, PointRecord
from apps.reports.models import Report


def ensure_point_record(member, *, amount: int, source_type: str, source_id: str, reason: str, operator=None):
    change_type = PointRecord.ChangeType.INCOME if amount > 0 else PointRecord.ChangeType.EXPENSE
    record, _ = PointRecord.objects.update_or_create(
        member=member,
        source_type=source_type,
        source_id=source_id,
        defaults={
            "amount": amount,
            "change_type": change_type,
            "reason": reason,
            "operator": operator,
        },
    )
    return record


def refresh_point_account(member):
    balance = sum(PointRecord.objects.filter(member=member).values_list("amount", flat=True))
    account, _ = PointAccount.objects.get_or_create(member=member)
    account.balance = balance
    account.save(update_fields=["balance"])
    return account


class Command(BaseCommand):
    help = "创建一期 MVP 前端开发和验收测试数据。"

    def handle(self, *args, **options):
        User = get_user_model()
        now = timezone.now()
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
            openid="test-openid",
            defaults={"nickname": "前端测试用户", "phone": "13800000000", "is_active": True},
        )
        Member.objects.update_or_create(
            openid="test-member-openid",
            defaults={"nickname": "兼容测试用户", "phone": "13800000001", "is_active": True},
        )

        merchant, _ = Merchant.objects.update_or_create(
            openid="merchant-openid",
            defaults={"name": "便民超市", "contact_name": "王店长", "phone": "13900000000", "address": "幸福街道便民服务点", "is_active": True},
        )
        Merchant.objects.update_or_create(
            openid="test-merchant-openid",
            defaults={"name": "兼容测试商户", "contact_name": "商户联系人", "phone": "13900000001", "address": "测试街道", "is_active": True},
        )
        other_merchant, _ = Merchant.objects.update_or_create(
            openid="bakery-merchant-openid",
            defaults={"name": "暖心面包房", "contact_name": "李店长", "phone": "13900000002", "address": "邻里中心一层", "is_active": True},
        )

        safety_content, _ = LearningContent.objects.update_or_create(
            title="街道服务安全学习",
            defaults={"body": "学习街道服务中的安全规范、应急联系人和上报流程。", "points": 5, "required_seconds": 60, "is_active": True},
        )
        LearningContent.objects.update_or_create(
            title="社区志愿服务指引",
            defaults={"body": "了解社区活动报名、签到、服务反馈和积分获取方式。", "points": 6, "required_seconds": 90, "is_active": True},
        )
        LearningContent.objects.update_or_create(
            title="积分兑换规则说明",
            defaults={"body": "介绍积分获取、商品兑换、商户交付核销和记录查询流程。", "points": 0, "required_seconds": 30, "is_active": True},
        )

        learning_record = ensure_point_record(
            member,
            amount=5,
            source_type=PointRecord.SourceType.LEARNING,
            source_id=f"seed-learning-{safety_content.id}",
            reason=f"完成学习：{safety_content.title}",
        )
        LearningRecord.objects.update_or_create(
            member=member,
            content=safety_content,
            defaults={"learned_seconds": 90, "is_completed": True, "completed_at": now, "point_record": learning_record},
        )

        volunteer_activity, _ = Activity.objects.update_or_create(
            title="社区志愿活动",
            defaults={
                "body": "协助社区开展便民宣传、秩序维护和居民引导。",
                "location": "社区中心",
                "start_time": now + timezone.timedelta(days=1),
                "end_time": now + timezone.timedelta(days=1, hours=2),
                "points": 8,
                "status": Activity.Status.PUBLISHED,
            },
        )
        Activity.objects.update_or_create(
            title="垃圾分类宣传活动",
            defaults={
                "body": "面向居民宣传垃圾分类规则，协助发放宣传材料。",
                "location": "幸福小区南门",
                "start_time": now + timezone.timedelta(days=3),
                "end_time": now + timezone.timedelta(days=3, hours=2),
                "points": 6,
                "status": Activity.Status.PUBLISHED,
            },
        )
        ActivitySignup.objects.update_or_create(member=member, activity=volunteer_activity, defaults={})
        ActivityCheckin.objects.update_or_create(
            member=member,
            activity=volunteer_activity,
            defaults={"status": ActivityCheckin.Status.PENDING, "review_comment": ""},
        )

        elder_task, _ = ElderServiceTask.objects.update_or_create(
            title="探访老人服务",
            defaults={"description": "协助社区探访独居老人，记录基本需求并反馈给工作人员。", "location": "幸福小区", "points": 10, "status": ElderServiceTask.Status.PUBLISHED},
        )
        ElderServiceTask.objects.update_or_create(
            title="助老物资配送",
            defaults={"description": "为行动不便老人配送社区服务站准备的生活物资。", "location": "邻里服务站", "points": 8, "status": ElderServiceTask.Status.PUBLISHED},
        )
        ElderServiceFeedback.objects.update_or_create(
            member=member,
            task=elder_task,
            defaults={"content": "已完成探访，老人反馈需要后续协助维修楼道照明。", "status": ElderServiceFeedback.Status.PENDING, "review_comment": ""},
        )

        Report.objects.update_or_create(
            member=member,
            title="路灯故障上报",
            defaults={
                "description": "幸福小区 3 号楼旁路灯夜间不亮，影响居民通行。",
                "location": "幸福小区 3 号楼",
                "points": 5,
                "status": Report.Status.PENDING,
                "review_comment": "",
            },
        )

        rice_product, _ = MerchantProduct.objects.update_or_create(
            merchant=merchant,
            name="便民大米 1kg",
            defaults={"description": "社区便民兑换商品，适合作为积分商城基础兑换样例。", "points_required": 20, "is_active": True},
        )
        soap_product, _ = MerchantProduct.objects.update_or_create(
            merchant=merchant,
            name="家用香皂套装",
            defaults={"description": "商户交付后可在商户端确认核销。", "points_required": 15, "is_active": True},
        )
        MerchantProduct.objects.update_or_create(
            merchant=other_merchant,
            name="暖心面包券",
            defaults={"description": "用于验证商户端只能看到本商户兑换记录。", "points_required": 12, "is_active": True},
        )

        ensure_point_record(
            member,
            amount=120,
            source_type=PointRecord.SourceType.MANUAL,
            source_id="seed-welcome-points",
            reason="开发测试初始积分",
            operator=admin,
        )

        pending_redemption, _ = ProductRedemption.objects.update_or_create(
            merchant=merchant,
            product=rice_product,
            member=member,
            defaults={"points_spent": rice_product.points_required, "status": ProductRedemption.Status.PENDING},
        )
        pending_record = ensure_point_record(
            member,
            amount=-rice_product.points_required,
            source_type=PointRecord.SourceType.PRODUCT_REDEMPTION,
            source_id=f"seed-redemption-{pending_redemption.id}",
            reason=f"兑换商品：{rice_product.name}",
        )
        pending_redemption.point_record = pending_record
        pending_redemption.save(update_fields=["point_record"])

        completed_redemption, _ = ProductRedemption.objects.update_or_create(
            merchant=merchant,
            product=soap_product,
            member=member,
            defaults={"points_spent": soap_product.points_required, "status": ProductRedemption.Status.COMPLETED},
        )
        completed_record = ensure_point_record(
            member,
            amount=-soap_product.points_required,
            source_type=PointRecord.SourceType.PRODUCT_REDEMPTION,
            source_id=f"seed-redemption-{completed_redemption.id}",
            reason=f"兑换商品：{soap_product.name}",
        )
        completed_redemption.point_record = completed_record
        completed_redemption.save(update_fields=["point_record"])

        refresh_point_account(member)

        self.stdout.write(
            self.style.SUCCESS(
                f"MVP 前端开发数据已准备：用户 {member.openid}，商户 {merchant.openid}，后台 admin/admin123456"
            )
        )
