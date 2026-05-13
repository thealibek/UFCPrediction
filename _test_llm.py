"""Быстрый smoke-test текущего LLM провайдера."""
import os, time
from openai import OpenAI

def _load_env(path=".env.local"):
    if not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_env()

base_url = os.environ.get("LLM_BASE_URL")
api_key = os.environ.get("LLM_API_KEY")
model = os.environ.get("LLM_MODEL")

print(f"📡 Base URL: {base_url}")
print(f"🤖 Model:    {model}")
print(f"🔑 Key:      {api_key[:15]}..." if api_key else "❌ NO KEY")

client = OpenAI(api_key=api_key, base_url=base_url)
t0 = time.time()
try:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":"Отвечай кратко, на русском."},
            {"role":"user","content":"Карлос Пратес vs Джек Делла Мадалена в UFC. "
             "Кто фаворит и почему? 2 предложения максимум."},
        ],
        temperature=0.5, max_tokens=300,
    )
    dt = time.time() - t0
    txt = resp.choices[0].message.content
    print(f"\n✅ OK ({dt:.1f}s, {len(txt)} chars)")
    print("---")
    print(txt)
    print("---")
    # usage
    if hasattr(resp, "usage") and resp.usage:
        print(f"Tokens: prompt={resp.usage.prompt_tokens} "
              f"completion={resp.usage.completion_tokens}")
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
