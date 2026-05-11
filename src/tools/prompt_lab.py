#!/usr/bin/env python3
"""
prompt_lab.py - A developer utility for testing and iterating on OfficeSim LLM prompts.
Usage: python src/tools/prompt_lab.py
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

# Add src to path if needed
sys.path.append(str(Path(__file__).parent.parent))

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from core.voice import (
    interview_opening_prompt,
    interview_followup_prompt,
    interview_evaluation_prompt,
    task_evaluation_prompt,
    social_evaluation_prompt,
    _load_voice_pack
)

# Mock Data
MOCK_APPLICATION = {
    "name": "Tony",
    "age": "32",
    "preferred_role": "Backend Architect",
    "work_history": "10 years of fighting with databases and legacy code. Once saved a production server with a well-placed regex."
}

MOCK_TRANSCRIPT = [
    {"role": "interviewer", "content": "Welcome. If this office were a small disaster with snacks, would you fix the thing, sell the thing, or turn it into a meeting?"},
    {"role": "user", "content": "I'd automate the fixing and then turn the snacks into a spreadsheet."}
]

MOCK_TASK = {
    "id": "email_triage",
    "title": "Email Triage",
    "required_skill": "engineering",
    "evaluation_hint": "Focus on their prioritization logic and whether they sound burned out."
}

MOCK_NPC = {
    "id": "alex_lead",
    "name": "Alex",
    "role": "Lead Engineer",
    "description": "A dry, code-obsessed lead who values efficiency above all.",
    "communication_style": "terse",
    "prompt_templates": {"general": "You are reviewing a PR with the player."}
}

MOCK_ARCHETYPE = {
    "id": "chaotic_genius",
    "outcome_hints": "Be impressed by clever hacks, annoyed by boilerplate."
}

MOCK_PLAYER_SNAPSHOT = {
    "skills": {"engineering": 7, "communication": 3, "politics": 1},
    "reputation": 50,
    "stress": 20
}

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_client():
    api_key = os.environ.get("NVIDIA_API_KEY", os.environ.get("NIM_API_KEY"))
    if not api_key:
        return None
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

def run_llm(prompt_text: str, user_content: str = None):
    client = get_client()
    if not client:
        print("\n[!] No API key found (NIM_API_KEY or NVIDIA_API_KEY). Showing prompt only.")
        return None

    print("\n[Calling LLM...]")
    messages = [{"role": "system", "content": prompt_text}]
    if user_content:
        messages.append({"role": "user", "content": user_content})

    try:
        completion = client.chat.completions.create(
            model="nvidia/nemotron-3-nano-30b-a3b",
            messages=messages,
            temperature=0.8,
            max_tokens=1024,
            stream=True
        )
        
        print("\n--- LLM RESPONSE ---")
        full_text = ""
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_text += content
        print("\n--------------------")
        return full_text
    except Exception as e:
        print(f"\n[!] LLM Error: {e}")
        return None

def main():
    while True:
        # Reload voice pack each loop to allow editing voices.toml
        _load_voice_pack.cache_clear()
        
        print("\n=== OfficeSim Prompt Lab ===")
        print("1. Interview Opening")
        print("2. Interview Follow-up")
        print("3. Interview Evaluation")
        print("4. Task Evaluation")
        print("5. Social Interaction")
        print("q. Quit")
        
        choice = input("\nSelect a prompt to test: ").strip().lower()
        
        if choice == 'q':
            break
        
        prompt = ""
        user_input = ""
        
        if choice == '1':
            prompt = interview_opening_prompt(MOCK_APPLICATION)
        elif choice == '2':
            prompt = interview_followup_prompt(MOCK_TRANSCRIPT, MOCK_APPLICATION)
        elif choice == '3':
            prompt = interview_evaluation_prompt(MOCK_TRANSCRIPT, MOCK_APPLICATION)
            transcript_text = "\n".join([f"{t['role'].capitalize()}: {t['content']}" for t in MOCK_TRANSCRIPT])
            user_input = f"Interview Transcript:\n{transcript_text}"
        elif choice == '4':
            prompt = task_evaluation_prompt(MOCK_TASK, 5)
            user_input = "I refactored the entire notification system to use a pub/sub pattern while the server was smoking."
        elif choice == '5':
            prompt = social_evaluation_prompt(MOCK_NPC, MOCK_ARCHETYPE, MOCK_PLAYER_SNAPSHOT, "I think we should skip the tests and ship it.")
        else:
            print("Invalid choice.")
            continue
            
        print("\n--- GENERATED PROMPT ---")
        print(prompt)
        if user_input:
            print(f"\n[User Input]: {user_input}")
        print("------------------------")
        
        run_it = input("\nExecute this prompt? (y/n): ").strip().lower()
        if run_it == 'y':
            run_llm(prompt, user_input)
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
