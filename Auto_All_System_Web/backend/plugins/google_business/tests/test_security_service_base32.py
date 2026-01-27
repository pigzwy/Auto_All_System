from django.test import SimpleTestCase

from plugins.google_business.services.security_service import GoogleSecurityService


class TestGoogleSecurityServiceBase32(SimpleTestCase):
    def setUp(self):
        # Avoid __init__ which touches browser manager.
        self.svc = GoogleSecurityService.__new__(GoogleSecurityService)

    def test_normalize_base32_secret(self):
        self.assertEqual(GoogleSecurityService._normalize_base32_secret(""), "")
        self.assertEqual(GoogleSecurityService._normalize_base32_secret(" ab cd "), "ABCD")
        self.assertEqual(
            GoogleSecurityService._normalize_base32_secret("jbsw y3dp ehpk 3pxp"),
            "JBSWY3DPEHPK3PXP",
        )

    def test_is_plausible_base32_secret(self):
        # Valid Base32 (A-Z2-7), length multiple of 8.
        self.assertTrue(self.svc._is_plausible_base32_secret("JBSWY3DPEHPK3PXP"))

        # Invalid chars.
        self.assertFalse(self.svc._is_plausible_base32_secret("JBSWY3DPEHPK3PXP1"))

        # Too short.
        self.assertFalse(self.svc._is_plausible_base32_secret("ABCDEFGH"))

        # Not multiple of 8.
        self.assertFalse(self.svc._is_plausible_base32_secret("JBSWY3DPEHPK3PX"))
