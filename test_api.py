from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

response = client.chat.completions.create(
    model="deepseek/deepseek-r1",
    messages=[
        {"role": "user", "content": "Say hello and explain AI in one line"}
    ]
)

print(response.choices[0].message.content)