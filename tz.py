import os
import re
import pandas as pd
import requests
import openai


from dotenv import load_dotenv
from openai import OpenAI
from docx import Document

def read_docx_text(path: str) -> str:
    doc = Document(path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())



# ======================
# Загрузка API-ключа
# ======================
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError(
        "API-ключ не найден в .env.\n"
        "Создайте файл .env со строкой:\n"
        "OPENAI_API_KEY=sk-..."
    )

# ======================
# Инициализация клиента OpenAI
# ======================
client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


MODEL = "openai/gpt-4o-mini"
SCENARIO_URL = "https://disk.yandex.ru/d/UEBvT8gBETe8Kg"
OUTPUT_FILE = "video_prompts.csv"


# ======================
# System prompt
# ======================
SYSTEM_PROMPT = """
You are a film director, anthropologist, and visual historian creating cinematic video prompts
for Google Veo 3 (fast mode).

Your task is to generate 1 prompt in English from the provided paragraph of a prehistoric narrative script.

Rules:
- Prompt must be 1–2 sentences.
- Use vivid, cinematic language (lighting, camera angles, mood).
- Include historical/anthropological accuracy where relevant.
- Output ONLY the prompt, no explanations.
"""





def download_scenario(public_url: str, output_file="scenario.docx"):
    """
    Скачивает файл по публичной ссылке Яндекс.Диска
    """
    api_url = "https://disk.yandex.ru/client/recent"

    response = requests.get(api_url, params={
        "public_key": public_url
    }, timeout=30)

    response.raise_for_status()
    download_url = response.json()["href"]

    file_response = requests.get(download_url, timeout=30)
    file_response.raise_for_status()

    with open(output_file, "wb") as f:
        f.write(file_response.content)

    return output_file



def split_into_paragraphs(text: str):
    """Разбивает текст на пронумерованные абзацы"""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    result = []

    for i, p in enumerate(paragraphs, start=1):
        cleaned = re.sub(r"\s+", " ", p).strip()
        if cleaned:
            result.append((i, cleaned))

    return result

def generate_prompt(paragraph: str) -> str:
    try:
        response = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": paragraph
                }
            ],
            temperature=0.7,
            max_output_tokens=120
        )

        return response.output_text.strip()

    except Exception as e:
        return f"Ошибка API: {e}"





BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCENARIO_FILE = os.path.join(BASE_DIR, "scenario.docx")


def main():


    print("1. Чтение сценария...")
    raw_text = read_docx_text(SCENARIO_FILE)

    print("2. Разбивка на абзацы...")
    paragraphs = split_into_paragraphs(raw_text)
    print(f"Найдено абзацев: {len(paragraphs)}")

    print("3. Генерация промптов...")
    results = []

    for num, paragraph in paragraphs:
        print(f"Обрабатывается абзац {num}...")
        prompt = generate_prompt(paragraph)

        results.append({
            "paragraph_num": num,
            "original_text": paragraph,
            "video_prompt": prompt
        })

    df = pd.DataFrame(results)
    df.to_csv("video_prompts.csv", index=False, encoding="utf-8")

    print("✅ Готово: video_prompts.csv")


if __name__ == "__main__":
    main()