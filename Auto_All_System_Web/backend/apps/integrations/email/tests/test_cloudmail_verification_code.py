from django.test import SimpleTestCase

from apps.integrations.email.services.client import CloudMailClient, Email


class TestCloudMailVerificationCode(SimpleTestCase):
    def setUp(self):
        # Avoid __init__ (httpx.Client); extraction doesn't need it.
        self.client = CloudMailClient.__new__(CloudMailClient)

    def _email(self, text: str) -> Email:
        return Email(
            email_id=1,
            sender_email="noreply@example.com",
            sender_name="",
            subject="Verification",
            to_email="user@example.com",
            to_name="",
            create_time="",
            email_type=0,
            content="",
            text=text,
        )

    def test_extract_verification_code_english_patterns(self):
        self.assertEqual(
            self.client.extract_verification_code(
                self._email("Your verification code: 123456")
            ),
            "123456",
        )
        self.assertEqual(
            self.client.extract_verification_code(self._email("code: 654321")),
            "654321",
        )
        self.assertEqual(
            self.client.extract_verification_code(
                self._email("123456 is your Google verification code")
            ),
            "123456",
        )

    def test_extract_verification_code_chinese_patterns(self):
        self.assertEqual(
            self.client.extract_verification_code(self._email("验证码：112233")),
            "112233",
        )
