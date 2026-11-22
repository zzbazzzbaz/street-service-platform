from django.conf import settings
from django.test import SimpleTestCase


class SimpleUISettingsTests(SimpleTestCase):
    def test_default_allowed_hosts_include_frp_admin_domain(self):
        self.assertIn("8000.example.com", settings.ALLOWED_HOSTS)

    def test_default_csrf_trusted_origins_include_frp_admin_domain(self):
        self.assertIn("http://8000.example.com", settings.CSRF_TRUSTED_ORIGINS)
        self.assertIn("https://8000.example.com", settings.CSRF_TRUSTED_ORIGINS)

    def test_simpleui_admin_menu_is_explicitly_configured(self):
        self.assertEqual(settings.INSTALLED_APPS[0], "simpleui")
        self.assertTrue(hasattr(settings, "SIMPLEUI_HOME_INFO"))
        self.assertTrue(hasattr(settings, "SIMPLEUI_ANALYSIS"))
        self.assertTrue(hasattr(settings, "SIMPLEUI_HOME_ACTION"))
        self.assertTrue(hasattr(settings, "SIMPLEUI_CONFIG"))

        self.assertFalse(settings.SIMPLEUI_HOME_INFO)
        self.assertFalse(settings.SIMPLEUI_ANALYSIS)
        self.assertFalse(settings.SIMPLEUI_HOME_ACTION)

        config = settings.SIMPLEUI_CONFIG

        self.assertFalse(config["system_keep"])
        self.assertFalse(config["dynamic"])
        self.assertEqual(
            [menu["name"] for menu in config["menus"]],
            ["用户管理", "学习宣传", "随手上报", "活动管理", "助老服务", "积分与商户", "后台账号"],
        )

        model_urls = {
            model["url"]
            for menu in config["menus"]
            for model in menu["models"]
        }
        self.assertEqual(
            model_urls,
            {
                "/admin/members/member/",
                "/admin/learning/learningcontent/",
                "/admin/learning/learningrecord/",
                "/admin/reports/report/",
                "/admin/civic_feedbacks/civicfeedback/",
                "/admin/problem_feedbacks/problemfeedback/",
                "/admin/activities/activity/",
                "/admin/activities/activitysignup/",
                "/admin/activities/activitycheckin/",
                "/admin/elder_services/elderservicetask/",
                "/admin/elder_services/eldercarerelation/",
                "/admin/elder_services/elderservicefeedback/",
                "/admin/points/pointaccount/",
                "/admin/points/pointrecord/",
                "/admin/points/manualpointadjustment/",
                "/admin/points/pointexchangerule/",
                "/admin/merchants/merchant/",
                "/admin/merchants/merchantsettlement/",
                "/admin/accounts/user/",
            },
        )
