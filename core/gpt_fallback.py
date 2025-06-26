
import openai
from config import OPENAI_API_KEY, GPT_MODEL

openai.api_key = OPENAI_API_KEY

PROMPT_TEMPLATE = """
Please convert the following MLBB account line into this exact format:

email:password | uid = 123456789 (server_id) | name = NAME | max_rank = RANK | level = 99 | country = XX | is_banned = False | credits = Config by RZX

Only respond with the corrected line. Do not add any comments or explanations.

Line:
{}
"""

async def fix_line_with_gpt(line: str) -> str | None:
    try:
        response = await openai.ChatCompletion.acreate(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a data formatting assistant."},
                {"role": "user", "content": PROMPT_TEMPLATE.format(line.strip())}
            ],
            temperature=0.3
        )
        fixed_line = response.choices[0].message.content.strip()
        return fixed_line if ":" in fixed_line and "|" in fixed_line else None
    except Exception as e:
        print("GPT error:", e)
        return None
