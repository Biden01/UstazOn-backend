"""
AI Service for chatbot functionality using Google Gemini API and OpenAI GPT
"""
import logging
import json
import asyncio
from typing import Any, AsyncGenerator
from functools import partial
from pydantic import ValidationError
from fastapi import HTTPException

from google import genai
from openai import AsyncOpenAI
from src.core.config import settings
from src.schemas.ai_schemas import PresentationData, TestData

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI chat using Google Gemini models"""

    # Available AI models
    AVAILABLE_MODELS = {
        # Google Gemini models
        "gemini-2.5-flash": {
            "name": "Gemini 2.5 Flash",
            "provider": "Google",
            "description": "Быстрая и экономичная модель",
            "cost": "low",
            "quality": "good",
            "speed": "very_fast",
            "use_cases": ["Презентации", "Быстрые ответы", "Общение"]
        },
        "gemini-2.0-flash-exp": {
            "name": "Gemini 2.0 Flash Experimental",
            "provider": "Google",
            "description": "Экспериментальная быстрая модель",
            "cost": "low",
            "quality": "good",
            "speed": "very_fast",
            "use_cases": ["Тестирование новых функций"]
        },

        # Anthropic Claude models (требуют API ключ)
        "claude-3.5-sonnet": {
            "name": "Claude 3.5 Sonnet",
            "provider": "Anthropic",
            "description": "Лучшее качество для образования",
            "cost": "high",
            "quality": "excellent",
            "speed": "medium",
            "use_cases": ["Качественные презентации", "Методички", "Планы уроков"],
            "requires_api_key": True
        },
        "claude-3-haiku": {
            "name": "Claude 3 Haiku",
            "provider": "Anthropic",
            "description": "Быстрая модель от Anthropic",
            "cost": "low",
            "quality": "good",
            "speed": "very_fast",
            "use_cases": ["Быстрые ответы", "Общение"],
            "requires_api_key": True
        },
        # OpenAI GPT models (требуют API ключ)
        # OpenAI GPT models (требуют API ключ)
        "gpt-4o": {
            "name": "GPT-4o",
            "provider": "OpenAI",
            "description": "Флагманская модель OpenAI",
            "cost": "very_high",
            "quality": "excellent",
            "speed": "fast",
            "use_cases": ["Сложные задачи", "Визуал", "Креативность"],
            "requires_api_key": True
        },
        "gpt-4o-mini": {
            "name": "GPT-4o Mini",
            "provider": "OpenAI",
            "description": "Быстрая и умная модель OpenAI",
            "cost": "low",
            "quality": "good",
            "speed": "very_fast",
            "use_cases": ["Общение", "Простые задачи"],
            "requires_api_key": True
        },
        "gpt-4-turbo": {
            "name": "GPT-4 Turbo",
            "provider": "OpenAI",
            "description": "Мощная модель OpenAI",
            "cost": "very_high",
            "quality": "excellent",
            "speed": "medium",
            "use_cases": ["Сложные задачи", "Креативность"],
            "requires_api_key": True
        },
        "gpt-3.5-turbo": {
            "name": "GPT-3.5 Turbo",
            "provider": "OpenAI",
            "description": "Быстрая модель GPT",
            "cost": "low",
            "quality": "good",
            "speed": "very_fast",
            "use_cases": ["Общение", "Простые задачи"],
            "requires_api_key": True
        }
    }

    def __init__(self):
        """Initialize AI services (Gemini and OpenAI)"""
        # Initialize Google Gemini client
        self.gemini_client = None
        if settings.GOOGLE_AI_KEY:
            try:
                self.gemini_client = genai.Client(api_key=settings.GOOGLE_AI_KEY)
                logger.info("Google Gemini service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
        else:
            logger.warning("GOOGLE_AI_KEY not set in environment variables")

        # Initialize OpenAI client
        self.openai_client = None
        if settings.OPENAI_API_KEY:
            try:
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("OPENAI_API_KEY not set in environment variables")
            
        # Initialize Anthropic Key
        self.anthropic_key = settings.ANTHROPIC_API_KEY if hasattr(settings, "ANTHROPIC_API_KEY") else None
        if not self.anthropic_key:
             # Fallback: try getting from env directly if not in settings schema
            import os
            self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            
        if self.anthropic_key:
             logger.info("Anthropic service initialized (using raw HTTP)")
        else:
             logger.warning("ANTHROPIC_API_KEY not set")

        # Set default model and client
        self.default_model = "gemini-2.5-flash"
        self.client = self.gemini_client  # For backward compatibility

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_instruction: str | None = None,
        images: list[bytes] | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a message to AI and get a response

        Args:
            message: User's message
            history: Optional conversation history
            system_instruction: Optional system prompt
            images: Optional list of image bytes to analyze
            model: Optional model name (defaults to gemini-2.5-flash)

        Returns:
            dict with 'text' and 'usage' keys
        """
        # Use provided model or default
        model_name = model or self.default_model

        # Validate model
        if model_name not in self.AVAILABLE_MODELS:
            logger.warning(f"Unknown model {model_name}, using default {self.default_model}")
            model_name = self.default_model

        # Determine provider
        provider = self.AVAILABLE_MODELS[model_name]["provider"]

        # Route to appropriate provider
        if provider == "OpenAI":
            return await self._chat_openai(message, history, system_instruction, images, model_name)
        elif provider == "Anthropic":
            return await self._chat_anthropic(message, history, system_instruction, images, model_name)
        else:
            return await self._chat_gemini(message, history, system_instruction, images, model_name)

    async def _chat_anthropic(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_instruction: str | None = None,
        images: list[bytes] | None = None,
        model_name: str = "claude-3-5-sonnet-20240620",
    ) -> dict[str, Any]:
        """Handle chat with Anthropic Claude models via raw HTTP"""
        if not self.anthropic_key:
            raise ValueError("Anthropic service not initialized. Please set ANTHROPIC_API_KEY.")

        import httpx
        import base64

        try:
            # Map simplified model names to actual API versions if needed
            api_model = model_name
            if model_name == "claude-3.5-sonnet":
                api_model = "claude-3-5-sonnet-20240620"
            elif model_name == "claude-3-haiku":
                api_model = "claude-3-haiku-20240307"

            messages = []
            
            # History
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    if role == "model": role = "assistant"
                    messages.append({
                        "role": role,
                        "content": msg.get("content", "")
                    })

            # User message
            content = []
            if images:
                for img_bytes in images:
                    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_b64
                        }
                    })
            
            content.append({"type": "text", "text": message})
            messages.append({"role": "user", "content": content})

            headers = {
                "x-api-key": self.anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            payload = {
                "model": api_model,
                "max_tokens": 4096,
                "messages": messages
            }
            
            if system_instruction:
                payload["system"] = system_instruction

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"Anthropic API Error: {response.text}")
                
                data = response.json()
                text = data["content"][0]["text"]
                
                usage = {
                    "input_tokens": data["usage"]["input_tokens"],
                    "output_tokens": data["usage"]["output_tokens"],
                    "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                }
                
                return {"text": text, "usage": usage}

        except Exception as e:
            logger.error(f"Error in Anthropic chat: {e}")
            raise

    async def _chat_gemini(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_instruction: str | None = None,
        images: list[bytes] | None = None,
        model_name: str = "gemini-2.5-flash",
    ) -> dict[str, Any]:
        """Handle chat with Google Gemini models"""
        if not self.gemini_client:
            raise ValueError("Gemini service not initialized. Please set GOOGLE_AI_KEY.")

        try:
            # Build contents list
            contents = []

            # Add system instruction as first user message if provided
            if system_instruction:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"System instruction: {system_instruction}"}]
                })
                # Add model acknowledgment
                contents.append({
                    "role": "model",
                    "parts": [{"text": "Understood. I'll follow these instructions."}]
                })

            # Add conversation history if provided
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    # Convert "model" to "assistant" if needed
                    if role == "model":
                        role = "model"
                    elif role == "assistant":
                        role = "model"

                    contents.append({
                        "role": role,
                        "parts": [{"text": msg.get("content", "")}]
                    })

            # Add current user message with optional images
            parts = [{"text": message}]

            # Add images if provided
            if images:
                import base64
                for img_bytes in images:
                    # Convert bytes to base64
                    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                    parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",  # Gemini supports jpeg, png, webp
                            "data": img_b64
                        }
                    })

            contents.append({
                "role": "user",
                "parts": parts
            })

            # Call Gemini API synchronously in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(
                    self.gemini_client.models.generate_content,
                    model=model_name,
                    contents=contents
                )
            )

            # Extract response text
            text = response.text

            # Extract usage metadata (if available)
            usage = {
                "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0) if hasattr(response, "usage_metadata") else 0,
                "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0) if hasattr(response, "usage_metadata") else 0,
                "total_tokens": getattr(response.usage_metadata, "total_token_count", 0) if hasattr(response, "usage_metadata") else 0,
            }

            return {"text": text, "usage": usage}

        except Exception as e:
            logger.error(f"Error in Gemini chat: {e}")
            raise

    async def _chat_openai(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_instruction: str | None = None,
        images: list[bytes] | None = None,
        model_name: str = "gpt-3.5-turbo",
    ) -> dict[str, Any]:
        """Handle chat with OpenAI GPT models"""
        if not self.openai_client:
            raise ValueError("OpenAI service not initialized. Please set OPENAI_API_KEY.")

        try:
            # Build messages list
            messages = []

            # Add system instruction if provided
            if system_instruction:
                messages.append({
                    "role": "system",
                    "content": system_instruction
                })

            # Add conversation history if provided
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    # Convert "model" to "assistant" for OpenAI
                    if role == "model":
                        role = "assistant"

                    messages.append({
                        "role": role,
                        "content": msg.get("content", "")
                    })

            # Add current user message
            if images:
                # GPT-4 Vision support
                import base64
                content = [{"type": "text", "text": message}]

                for img_bytes in images:
                    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}"
                        }
                    })

                messages.append({
                    "role": "user",
                    "content": content
                })
            else:
                messages.append({
                    "role": "user",
                    "content": message
                })

            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=model_name,
                messages=messages
            )

            # Extract response text
            text = response.choices[0].message.content

            # Extract usage metadata
            usage = {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            return {"text": text, "usage": usage}

        except Exception as e:
            logger.error(f"Error in OpenAI chat: {e}")
            raise

    async def chat_stream(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_instruction: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI chat response in real-time

        Args:
            message: User's message
            history: Optional conversation history
            system_instruction: Optional system prompt

        Yields:
            Chunks of text as they arrive
        """
        if not self.client:
            raise ValueError("AI service not initialized. Please set GOOGLE_AI_KEY.")

        try:
            # Build contents list (same as chat method)
            contents = []

            if system_instruction:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"System instruction: {system_instruction}"}]
                })
                contents.append({
                    "role": "model",
                    "parts": [{"text": "Understood. I'll follow these instructions."}]
                })

            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    if role == "assistant":
                        role = "model"

                    contents.append({
                        "role": role,
                        "parts": [{"text": msg.get("content", "")}]
                    })

            contents.append({
                "role": "user",
                "parts": [{"text": message}]
            })

            # Stream response
            # Note: google-genai SDK streaming support varies
            # For now, just return the full response
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=contents
                )
            )

            # Yield the full text (streaming support can be added later)
            yield response.text

        except Exception as e:
            logger.error(f"Error in AI chat stream: {e}")
            raise

    def get_available_models(self, include_unavailable: bool = False) -> dict[str, dict]:
        """
        Get list of available AI models

        Args:
            include_unavailable: Include models that require API keys not configured

        Returns:
            dict with model IDs as keys and model info as values
        """
        if include_unavailable:
            return self.AVAILABLE_MODELS

        # Filter only models that are available (have API keys configured)
        available = {}
        for model_id, model_info in self.AVAILABLE_MODELS.items():
            provider = model_info.get("provider")

            # Check availability based on provider
            is_available = False

            if provider == "Google":
                is_available = self.gemini_client is not None
            elif provider == "OpenAI":
                is_available = self.openai_client is not None
            elif provider == "Anthropic":
                is_available = self.anthropic_key is not None

            if is_available or include_unavailable:
                available[model_id] = {**model_info, "available": is_available}

        return available

    async def generate_with_retry(
        self, 
        prompt: str, 
        max_retries: int = 2,
        system_instruction: str = "You are an expert educational assistant.",
        model: str = "gemini-2.5-flash"
    ):
        """
        Generate response with retry strategy as specified in Task 6
        
        Args:
            prompt: Input prompt for AI
            max_retries: Maximum number of retry attempts (default 2)
            system_instruction: System instruction for the AI
            model: AI model to use
            
        Returns:
            Validated response data
        """
        for attempt in range(max_retries + 1):
            try:
                response = await self.chat(
                    message=prompt,
                    system_instruction=system_instruction,
                    model=model
                )
                
                # Attempt to parse and validate the response
                ai_response = response["text"].strip()
                
                # Clean up markdown code blocks
                import re
                ai_response = re.sub(r'```json\s*', '', ai_response)
                ai_response = re.sub(r'```\s*$', '', ai_response)
                ai_response = ai_response.strip()
                
                # Parse JSON
                try:
                    data = json.loads(ai_response)
                except json.JSONDecodeError:
                    # Try to extract JSON from the response
                    json_match = re.search(r'\{[\s\S]*\}', ai_response)
                    if json_match:
                        data = json.loads(json_match.group())
                    else:
                        raise json.JSONDecodeError("Failed to parse JSON from AI response", ai_response, 0)
                
                return data
                
            except json.JSONDecodeError:
                if attempt == max_retries:
                    # Final attempt failed with JSON parsing
                    raise HTTPException(
                        status_code=400, 
                        detail="AI failed to generate valid JSON after retries"
                    )
                else:
                    # On first attempt, try with stricter prompt for next attempt
                    system_instruction = system_instruction + " Return ONLY valid JSON without any additional text or explanations."
                    continue
            except ValidationError as e:
                if attempt == max_retries:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"AI output validation failed: {str(e)}"
                    )
                else:
                    # Retry with stricter instructions
                    system_instruction = system_instruction + " Strictly follow the required output format."
                    continue
            except asyncio.TimeoutError:
                if attempt == max_retries:
                    raise HTTPException(
                        status_code=504, 
                        detail="AI generation timeout after retries"
                    )
                else:
                    # Continue to next attempt
                    continue
            except Exception as e:
                if attempt == max_retries:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"AI generation failed: {str(e)}"
                    )
                else:
                    # Continue to next attempt
                    continue
                    
        # This should never be reached due to the loop condition
        raise HTTPException(
            status_code=500, 
            detail="AI generation failed after maximum retries"
        )


# Global AI service instance
ai_service = AIService()
