from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.voice import interview_followup_prompt, interview_opening_prompt
from systems import onboarding


APPLICATION = {
    "name": "Casey",
    "age": "34",
    "preferred_role": "sales-product chaos translator",
    "work_history": "Ran demos, survived roadmap meetings, and made one spreadsheet people still fear.",
}


class OnboardingApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old_nvidia_key = os.environ.pop("NVIDIA_API_KEY", None)
        self.old_nim_key = os.environ.pop("NIM_API_KEY", None)

    def tearDown(self) -> None:
        if self.old_nvidia_key is not None:
            os.environ["NVIDIA_API_KEY"] = self.old_nvidia_key
        if self.old_nim_key is not None:
            os.environ["NIM_API_KEY"] = self.old_nim_key

    def test_opening_prompt_includes_application_context(self) -> None:
        prompt = interview_opening_prompt(APPLICATION)
        self.assertIn("Casey", prompt)
        self.assertIn("sales-product chaos translator", prompt)
        self.assertIn("Do not treat age as a hiring criterion", prompt)

    def test_followup_prompt_includes_application_context(self) -> None:
        prompt = interview_followup_prompt(
            [{"role": "user", "content": "I would turn the outage into a client narrative."}],
            APPLICATION,
        )
        self.assertIn("roadmap meetings", prompt)
        self.assertIn("Use the application form as context", prompt)

    def test_initial_question_fallback_uses_application_detail(self) -> None:
        question = onboarding.get_initial_question(APPLICATION)
        self.assertIn("Casey", question)
        self.assertIn("sales-product chaos translator", question)

    def test_followup_fallback_uses_preferred_role(self) -> None:
        question = onboarding.get_next_question(
            [{"role": "interviewer", "content": "Opening?"}, {"role": "user", "content": "I pitch the deck."}],
            APPLICATION,
        )
        self.assertIn("sales-product chaos translator", question)


if __name__ == "__main__":
    unittest.main()
