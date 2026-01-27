from django.test import SimpleTestCase

from plugins.google_business.utils import upsert_geekez_profile_meta


class TestGeekezProfileMetaUtils(SimpleTestCase):
    def test_upsert_meta_new(self):
        meta = upsert_geekez_profile_meta(
            None,
            profile_id="p-1",
            profile_name="a@example.com",
            now_iso="2026-01-26T00:00:00+00:00",
            created_by_system=False,
            matched_on_import=True,
        )

        self.assertIn("geekez_profile", meta)
        profile = meta["geekez_profile"]
        self.assertEqual(profile["browser_type"], "geekez")
        self.assertEqual(profile["profile_id"], "p-1")
        self.assertEqual(profile["profile_name"], "a@example.com")
        self.assertFalse(profile["created_by_system"])
        self.assertEqual(profile["created_at"], "2026-01-26T00:00:00+00:00")
        self.assertTrue(profile["matched_on_import"])
        self.assertEqual(profile["matched_at"], "2026-01-26T00:00:00+00:00")

    def test_upsert_meta_preserves_created_at(self):
        existing = {
            "geekez_profile": {
                "browser_type": "geekez",
                "profile_id": "old",
                "profile_name": "old@example.com",
                "created_by_system": True,
                "created_at": "2020-01-01T00:00:00+00:00",
            }
        }

        meta = upsert_geekez_profile_meta(
            existing,
            profile_id="new",
            profile_name="new@example.com",
            now_iso="2026-01-26T00:00:00+00:00",
            created_by_system=None,
            matched_on_import=False,
        )

        profile = meta["geekez_profile"]
        self.assertEqual(profile["profile_id"], "new")
        self.assertEqual(profile["profile_name"], "new@example.com")
        self.assertTrue(profile["created_by_system"])
        self.assertEqual(profile["created_at"], "2020-01-01T00:00:00+00:00")
        self.assertNotIn("matched_on_import", profile)
        self.assertNotIn("matched_at", profile)
