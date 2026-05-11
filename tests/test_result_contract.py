from __future__ import annotations

import unittest

from src.systems.result_contract import empty_result, missing_result_keys, normalize_result


class ResultContractTests(unittest.TestCase):
    def test_empty_result_contains_standard_keys(self) -> None:
        result = empty_result()
        self.assertEqual(missing_result_keys(result), [])
        self.assertEqual(result["outcome"], "partial")
        self.assertEqual(result["npc_deltas"], {})

    def test_invalid_outcome_normalizes_to_partial(self) -> None:
        result = normalize_result({"outcome": "excellent", "rep_delta": 5})
        self.assertEqual(result["outcome"], "partial")
        self.assertEqual(result["rep_delta"], 5)

    def test_bad_nested_delta_shapes_are_sanitized(self) -> None:
        result = normalize_result({"skill_deltas": [], "npc_deltas": None})
        self.assertEqual(result["skill_deltas"], {})
        self.assertEqual(result["npc_deltas"], {})


if __name__ == "__main__":
    unittest.main()
