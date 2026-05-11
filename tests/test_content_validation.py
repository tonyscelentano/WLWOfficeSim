from __future__ import annotations

import unittest

from tools.content_validation import validate_content


class ContentValidationTests(unittest.TestCase):
    def test_project_content_has_no_validation_errors(self) -> None:
        report = validate_content()

        self.assertEqual(report.errors, [])


if __name__ == "__main__":
    unittest.main()
