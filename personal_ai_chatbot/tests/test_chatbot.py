import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from chatbot import PersonalChatbot, load_faqs, load_memory, relevant_faqs


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def chat(self, model: str, messages: list[dict[str, str]]) -> SimpleNamespace:
        self.calls.append({"model": model, "messages": messages})
        return SimpleNamespace(message=SimpleNamespace(content="A test reply."))


class ChatbotTests(unittest.TestCase):
    def test_relevant_faqs_match_query_terms(self) -> None:
        faqs = [
            {"question": "How do I reset my password?", "answer": "Use the reset page."},
            {"question": "Where is my calendar?", "answer": "It is in the office."},
        ]

        matches = relevant_faqs("Can you help me reset my password?", faqs)

        self.assertEqual([faqs[0]], matches)

    def test_faq_and_personal_facts_are_sent_to_ollama(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory_path = Path(directory) / "memory.json"
            client = FakeClient()
            faq = {"question": "How do I reset my password?", "answer": "Use the reset page."}
            chatbot = PersonalChatbot(
                client=client,
                model="test-model",
                faqs=[faq],
                memory={"facts": ["My name is Sam."], "messages": []},
                memory_path=memory_path,
            )

            answer = chatbot.reply("How do I reset my password?")

            system_prompt = client.calls[0]["messages"][0]["content"]
            self.assertEqual("A test reply.", answer)
            self.assertIn("My name is Sam.", system_prompt)
            self.assertIn("answer from that fact", system_prompt)
            self.assertIn("Use the reset page.", system_prompt)
            self.assertEqual("A test reply.", load_memory(memory_path)["messages"][-1]["content"])

    def test_facts_and_history_persist_and_can_be_cleared_independently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory_path = Path(directory) / "memory.json"
            client = FakeClient()
            chatbot = PersonalChatbot(
                client=client,
                model="test-model",
                faqs=[],
                memory=load_memory(memory_path),
                memory_path=memory_path,
            )

            self.assertFalse(chatbot.remember("  "))
            self.assertTrue(chatbot.remember("Favorite color: green"))
            self.assertFalse(chatbot.remember("favorite color: green"))
            chatbot.reply("Hello")
            chatbot.clear_history()

            saved_memory = load_memory(memory_path)
            self.assertEqual(["Favorite color: green"], saved_memory["facts"])
            self.assertEqual([], saved_memory["messages"])

            chatbot.forget_facts()
            self.assertEqual({"facts": [], "messages": []}, load_memory(memory_path))

    def test_invalid_faq_shape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            faq_path = Path(directory) / "faqs.json"
            faq_path.write_text(json.dumps({"question": "Not a list"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_faqs(faq_path)


if __name__ == "__main__":
    unittest.main()