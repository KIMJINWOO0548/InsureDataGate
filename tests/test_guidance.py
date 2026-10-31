"""Recovery guidance must help fix the cause without weakening the gate."""

import unittest

from insuredatagate.guidance import recovery


class RecoveryTests(unittest.TestCase):
    def test_version_reuse_requires_distinct_candidate_then_new_report(self):
        text = " ".join(recovery("VERSION_REUSED")["steps"]).lower()
        self.assertIn("distinct", text)
        self.assertIn("candidate", text)
        self.assertIn("new", text)
        self.assertNotIn("semver", text)

    def test_hash_mismatch_requires_confirming_intended_bytes(self):
        text = " ".join(recovery("HASH_MISMATCH")["steps"]).lower()
        self.assertIn("intended", text)
        self.assertIn("before", text)
        self.assertIn("hash", text)

    def test_identity_mismatch_does_not_suggest_renaming_to_pass(self):
        text = " ".join(recovery("DATASET_ID_MISMATCH")["steps"]).lower()
        self.assertIn("same dataset", text)
        self.assertIn("do not rename", text)

    def test_unreadable_snapshot_checks_limits_without_permission_escalation(self):
        text = " ".join(recovery("FILE_READ")["steps"]).lower()
        for word in ("exists", "regular", "limit", "existing access"):
            self.assertIn(word, text)
        self.assertNotIn("administrator", text)
        self.assertNotIn("chmod", text)

    def test_approval_errors_do_not_create_a_fictional_approver(self):
        for code in ("SOURCE_APPROVAL", "GOLD_APPROVAL", "SELF_REVIEW"):
            with self.subTest(code=code):
                text = " ".join(recovery(code)["steps"]).lower()
                self.assertIn("independent", text)
                self.assertIn("do not invent", text)

    def test_unknown_code_never_echoes_untrusted_content(self):
        result = recovery('<script>PRIVATE_VALUE</script>')
        self.assertNotIn("PRIVATE_VALUE", str(result))
        self.assertTrue(result["title"])
        self.assertTrue(result["steps"])
        result["steps"].clear()
        self.assertTrue(recovery("UNKNOWN")["steps"])


if __name__ == "__main__":
    unittest.main()
