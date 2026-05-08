import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def classify_user(ip: str, request_count: int, paths: list[str]) -> dict:
    path_summary = ", ".join(paths[-10:]) if paths else "none"
    
    prompt = f"""You are a rate limiting system. Analyze this user's behavior and classify them.

IP: {ip}
Requests in last 60 seconds: {request_count}
Recent endpoints hit: {path_summary}

Classify as one of:
- NORMAL: legitimate user, keep default limit
- AGGRESSIVE: hitting too many requests, reduce limit to 5/min
- BOT: clear bot pattern, reduce limit to 2/min
- HEAVY_USER: legitimate but high usage, increase limit to 30/min

Respond in this exact JSON format, nothing else:
{{"classification": "NORMAL", "limit": 10, "reason": "brief reason"}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    
    import json
    text = response.choices[0].message.content.strip()
    return json.loads(text)