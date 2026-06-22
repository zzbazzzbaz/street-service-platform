from django.test import SimpleTestCase, override_settings

from shared.auth import TokenError, issue_token, parse_token


class AuthToolsTests(SimpleTestCase):
    @override_settings(ACCESS_TOKEN_EXPIRES_SECONDS=3600)
    def test_issue_and_parse_member_token(self):
        token, expires_in = issue_token(subject_type="member", openid="member-openid")
        identity = parse_token(token)

        self.assertEqual(expires_in, 3600)
        self.assertEqual(identity.subject_type, "member")
        self.assertEqual(identity.openid, "member-openid")

    def test_issue_and_parse_merchant_token(self):
        token, _ = issue_token(subject_type="merchant", openid="merchant-openid")

        self.assertEqual(parse_token(token).subject_type, "merchant")
        self.assertEqual(parse_token(token).openid, "merchant-openid")

    def test_parse_rejects_bad_token(self):
        with self.assertRaisesRegex(TokenError, "token 格式错误"):
            parse_token("not-a-jwt")
