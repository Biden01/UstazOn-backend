import asyncio
import os
import sys

# Ensure backend root is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.services.ai_service import ai_service

async def verify_models():
    print("🚀 Verifying AI Models Configuration...")
    print("-" * 50)
    
    results = {}
    
    # 1. Test Gemini
    print("\n1. Testing Google Gemini (gemini-2.5-flash)...")
    try:
        res = await ai_service.chat(
            message="Hello Gemini, just say 'OK'",
            model="gemini-2.5-flash"
        )
        print(f"✅ Gemini Success: {res['text'].strip()}")
        results["gemini"] = True
    except Exception as e:
        print(f"❌ Gemini Failed: {e}")
        results["gemini"] = False

    # 2. Test OpenAI (GPT-4o)
    print("\n2. Testing OpenAI (gpt-4o)...")
    try:
        res = await ai_service.chat(
            message="Hello GPT, just say 'OK'",
            model="gpt-4o"
        )
        print(f"✅ GPT-4o Success: {res['text'].strip()}")
        results["openai"] = True
    except Exception as e:
        print(f"❌ GPT-4o Failed: {e}")
        results["openai"] = False

    # 3. Test Anthropic (Claude 3.5 Sonnet)
    print("\n3. Testing Anthropic (claude-3-5-sonnet)...")
    try:
        res = await ai_service.chat(
            message="Hello Claude, just say 'OK'",
            model="claude-3-5-sonnet"
        )
        print(f"✅ Claude Success: {res['text'].strip()}")
        results["anthropic"] = True
    except Exception as e:
        print(f"❌ Claude Failed: {e}")
        results["anthropic"] = False

    print("\n" + "-" * 50)
    print("SUMMARY")
    print("-" * 50)
    all_passed = True
    for model, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{model.capitalize()}: {status}")
        if not passed: all_passed = False
    
    if all_passed:
        print("\n🎉 ALL SYSTEMS GO! Your AI backend is fully operational.")
    else:
        print("\n⚠️ SOME CHECKS FAILED. Please check your .env keys.")

if __name__ == "__main__":
    asyncio.run(verify_models())
