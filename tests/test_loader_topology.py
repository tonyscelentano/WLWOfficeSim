from __future__ import annotations

import unittest

from src.core.loader import load_all


class LoaderTopologyTests(unittest.TestCase):
    def test_load_all_validates_npc_clusters_against_factions(self) -> None:
        data = load_all()
        self.assertIn("factions", data)
        self.assertIn("npcs", data)
        self.assertGreater(len(data["npcs"]), 0)


if __name__ == "__main__":
    unittest.main()
