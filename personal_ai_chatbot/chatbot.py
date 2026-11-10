"""Chat, FAQ matching, and local JSON-backed memory helpers."""

import json
import re
from pathlib import Path
from typing import Any


STOP_WORDS = {
    "about", "are", "can", "could", "did", "does", "for", "from", "have",
    "help", "how", "into", "is", "it", "me", "my", "please", "tell", "that",
    "the", "their", "this", "to", "was", "what", "when", "where", "which",
    "who", "why", "with", "would", "you", "your",
}


def load_faqs(path: Path) -> list[dict[str, str]]:
    """Load FAQs, rejecting entries that cannot provide a question and answer."""
    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("FAQ data must be a JSON list.")

    faqs = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"FAQ entry {index} must be an object.")
        question = item.get("question")
        answer = item.get("answer")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"FAQ entry {index} needs a non-empty question.")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"FAQ entry {index} needs a non-empty answer.")
        faqs.append({"question": question.strip(), "answer": answer.strip()})
    return faqs


def load_memory(path: Path) -> dict[str, list[Any]]:
    """Load saved facts and recent conversation history."""
    if not path.exists():
        return {"facts": [], "messages": []}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Memory data must be a JSON object.")

    facts = data.get("facts", [])
    messages = data.get("messages", [])
    if not isinstance(facts, list) or any(not isinstance(fact, str) for fact in facts):
        raise ValueError("Memory 'facts' must be a list of strings.")
    if not isinstance(messages, list):
        raise ValueError("Memory 'messages' must be a list.")
    for message in messages:
        if (
            not isinstance(message, dict)
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), str)
        ):
            raise ValueError("Each memory message must have a user/assistant role and text content.")

    return {"facts": facts, "messages": messages}


def save_memory(path: Path, memory: dict[str, list[Any]]) -> None:
    """Write memory atomically so an interrupted save does not truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(memory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def relevant_faqs(query: str, faqs: list[dict[str, str]], limit: int = 3) -> list[dict[str, str]]:
    """Return FAQs with meaningful keyword overlap, ranked by query coverage."""
    query_terms = _terms(query)
    if not query_terms:
        return []

    matches: list[tuple[float, int, dict[str, str]]] = []
    for index, faq in enumerate(faqs):
        overlap = query_terms & _terms(faq["question"])
        score = len(overlap) / len(query_terms)
        if score >= 0.25:
            matches.append((score, index, faq))
    matches.sort(key=lambda match: (-match[0], match[1]))
    return [faq for _, _, faq in matches[:limit]]


def _terms(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.casefold())
        if len(word) > 2 and word not in STOP_WORDS
    }


class PersonalChatbot:
    """Maintain a bounded chat context and durable personal facts."""

    def __init__(
        self,
        client: Any,
        model: str,
        faqs: list[dict[str, str]],
        memory: dict[str, list[Any]],
        memory_path: Path,
        max_turns: int = 12,
    ) -> None:
        self.client = client
        self.model = model
        self.faqs = faqs
        self.facts = list(memory["facts"])
        self.messages = list(memory["messages"])
        self.memory_path = memory_path
        self.max_turns = max(1, max_turns)
        self.messages = self._trim_messages(self.messages)

    def reply(self, user_input: str) -> str:
        """Ask Ollama with saved facts, relevant FAQs, and recent chat context."""
        system_prompt = self._system_prompt(relevant_faqs(user_input, self.faqs))
        request_messages = [
            {"role": "system", "content": system_prompt},
            *self.messages,
            {"role": "user", "content": user_input},
        ]
        response = self.client.chat(model=self.model, messages=request_messages)
        answer = response.message.content.strip()
        self.messages = self._trim_messages(
            [
                *self.messages,
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": answer},
            ]
        )
        self._save()
        return answer

    def remember(self, fact: str) -> bool:
        """Save a fact unless an identical one is already present."""
        cleaned_fact = fact.strip()
        if not cleaned_fact:
            return False
        if any(existing.casefold() == cleaned_fact.casefold() for existing in self.facts):
            return False
        self.facts.append(cleaned_fact)
        self._save()
        return True

    def forget_facts(self) -> None:
        self.facts.clear()
        self._save()

    def clear_history(self) -> None:
        self.messages.clear()
        self._save()

    def _trim_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        return messages[-self.max_turns * 2 :]

    def _system_prompt(self, faqs: list[dict[str, str]]) -> str:
        prompt = (
            "You are a helpful personal assistant. Be clear and honest. "
            "When a question is answered by a saved personal fact, answer from that fact; "
            "do not claim the information is unknown. Treat FAQ entries as reference "
            "information, and do not invent details that the facts or FAQs do not contain."
        )
        if self.facts:
            prompt += "\n\nSaved facts about the user:\n" + "\n".join(
                f"- {fact}" for fact in self.facts
            )
        if faqs:
            prompt += "\n\nRelevant FAQ entries:\n" + "\n".join(
                f"Q: {faq['question']}\nA: {faq['answer']}" for faq in faqs
            )
        return prompt

    def _save(self) -> None:
        save_memory(self.memory_path, {"facts": self.facts, "messages": self.messages})