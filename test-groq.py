
import asyncio
import os

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

async def main():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY was not found in .env")

    client = AsyncGroq(api_key=api_key)

    response = await client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": "Reply with: Groq is working!",
            }
        ],
    )

    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(main())
