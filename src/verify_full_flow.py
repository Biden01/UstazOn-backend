import asyncio
import os
import sys

# Ensure src is in python path
sys.path.append(os.getcwd())

from src.services.ai_service import ai_service
from src.services.manim_service import manim_service
from src.prompts.teacher_prompts import QUICK_PROMPTS
import re
import json

async def test_flow():
    print("--- Starting Manim Verification Flow ---")
    
    # 1. Test AI Generation
    topic = "Rotating Square loop"
    print(f"1. Requesting AI to generate code for: '{topic}'...")
    
    prompt_template = QUICK_PROMPTS["manim"]["prompt"]
    user_message = f"""Topic: {topic}
Level: low
{prompt_template}"""

    try:
        # Force using Gemini if available, or fallback
        model = "gemini-2.5-flash"
        print(f"   Using model: {model}")
        
        result = await ai_service.chat(
            message=user_message,
            system_instruction="You are a Manim expert.",
            model=model
        )
        
        ai_response = result["text"]
        print("   AI Response received (len):", len(ai_response))
        
        # Parse Code
        code = ""
        # Clean up response to get JSON
        clean_response = re.sub(r'```json\s*', '', ai_response)
        clean_response = re.sub(r'```\s*$', '', clean_response)
        clean_response = clean_response.strip()

        try:
            data = json.loads(clean_response)
            code = data.get("code", "")
        except:
             # Fallback
            code_match = re.search(r'```python(.*?)```', ai_response, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
        
        if not code:
            print("❌ FAILURE: Could not extract code from AI response.")
            print("Response:", ai_response[:500])
            return
            
        print("   Code extracted successfully.")
        print("   Code preview:", code[:100].replace('\n', ' '))

    except Exception as e:
        print(f"❌ FAILURE during AI Step: {e}")
        return

    # 2. Test Manim Rendering
    print("\n2. Sending code to ManimService...")
    try:
        video_path = manim_service.generate_video(code)
        print(f"✅ SUCCESS! Video generated at: {video_path}")
        
        if os.path.exists(video_path):
            size = os.path.getsize(video_path)
            print(f"   File size: {size / 1024 / 1024:.2f} MB")
        else:
            print("❌ File path returned but file missing!")
            
    except Exception as e:
        print(f"❌ FAILURE during Manim Rendering Step: {e}")
        # Print logs?

if __name__ == "__main__":
    asyncio.run(test_flow())
