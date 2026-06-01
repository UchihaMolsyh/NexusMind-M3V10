import asyncio
from core.llm import engine
from config import MODEL_PROFILE

async def test_gen():
    print("Loading model...")
    engine.load(MODEL_PROFILE)
    print("Model loaded.")
    
    messages = [{"role": "user", "content": "Hello!"}]
    print("Generating...")
    
    stream = engine.generate(messages=messages, max_tokens=20, stream=True)
    
    for chunk in stream:
        delta = chunk["choices"][0].get("delta", {}).get("content", "")
        if delta:
            print(delta, end="", flush=True)
            
    print("\nDone.")

asyncio.run(test_gen())
