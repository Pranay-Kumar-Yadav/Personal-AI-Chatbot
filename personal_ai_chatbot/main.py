"""Run the personal chatbot in a terminal using a local Ollama model."""

import os
from pathlib import Path

import ollama
from dotenv import load_dotenv

from chatbot import PersonalChatbot, load_faqs, load_memory


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"


def main() -> None:
    load_dotenv(PROJECT_DIR / ".env")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        max_turns = max(1, int(os.getenv("OLLAMA_MAX_TURNS", "12")))
        faqs = load_faqs(DATA_DIR / "faqs.json")
        memory = load_memory(DATA_DIR / "memory.json")
    except (OSError, ValueError) as error:
        print(f"Could not load chatbot data or settings: {error}")
        return

    chatbot = PersonalChatbot(
        client=ollama.Client(host=host),
        model=model,
        faqs=faqs,
        memory=memory,
        memory_path=DATA_DIR / "memory.json",
        max_turns=max_turns,
    )

    print(f"Personal AI Chatbot (Ollama: {model})")
    print("Type /help for commands. Your chat history and saved facts stay in data/memory.json.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        command, _, argument = user_input.partition(" ")
        if command == "/exit":
            print("Goodbye!")
            break
        if command == "/help":
            print(
                "Commands: /help, /clear, /remember <fact>, /memory, "
                "/forget, /faqs, /exit\n"
            )
            continue
        if command == "/clear":
            chatbot.clear_history()
            print("Conversation history cleared. Saved facts were kept.\n")
            continue
        if command == "/remember":
            if not argument.strip():
                print("Usage: /remember <fact>\n")
            elif chatbot.remember(argument):
                print("Saved that fact.\n")
            else:
                print("That fact is already saved.\n")
            continue
        if command == "/memory":
            if chatbot.facts:
                print("Saved facts:")
                for fact in chatbot.facts:
                    print(f"- {fact}")
            else:
                print("No saved facts yet. Use /remember <fact> to add one.")
            print(f"Stored conversation turns: {len(chatbot.messages) // 2}\n")
            continue
        if command == "/forget":
            chatbot.forget_facts()
            print("Saved facts forgotten. Conversation history was kept.\n")
            continue
        if command == "/faqs":
            if not faqs:
                print("No FAQs are configured in data/faqs.json.\n")
            else:
                for faq in faqs:
                    print(f"Q: {faq['question']}\nA: {faq['answer']}\n")
            continue
        if command.startswith("/"):
            print("Unknown command. Type /help to see available commands.\n")
            continue

        try:
            answer = chatbot.reply(user_input)
        except ollama.ResponseError as error:
            print(f"Ollama error: {error.error}")
            print(f"Check the model with: ollama pull {model}\n")
        except Exception as error:
            print(f"Ollama request failed: {error}")
            print("Check that Ollama is running and reachable at the configured host.\n")
        else:
            print(f"Bot: {answer}\n")


if __name__ == "__main__":
    main()