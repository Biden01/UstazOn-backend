"""
Gamma API Service for generating presentations.

Official documentation:
    https://developers.gamma.app/docs/generate-api-parameters-explained

Endpoints used:
    POST https://public-api.gamma.app/v1.0/generations
    GET  https://public-api.gamma.app/v1.0/generations/{generationId}

Authentication:
    Header  X-API-KEY: <key>
"""
import logging
import httpx
from src.core.config import settings

logger = logging.getLogger(__name__)

GAMMA_BASE_URL = "https://public-api.gamma.app/v1.0"


class GammaService:
    """Service for interacting with Gamma API v1.0"""

    def __init__(self):
        self.api_key = getattr(settings, "GAMMA_API_KEY", None)
        if not self.api_key:
            import os
            self.api_key = os.getenv("GAMMA_API_KEY")

        if not self.api_key:
            logger.warning("GAMMA_API_KEY not set in environment variables")
        else:
            logger.info("Gamma service initialized successfully")

    def _headers(self) -> dict:
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    async def generate_presentation(
        self,
        subject: str,
        grade: str,
        topic: str,
        slides_count: int = 12,
    ) -> str:
        """
        Start a presentation generation via Gamma Generate API.

        POST https://public-api.gamma.app/v1.0/generations

        Required fields: inputText, textMode.
        Optional: format, numCards, textOptions, imageOptions.

        Returns:
            generationId (str) — the Gamma generation identifier.
        """
        if not self.api_key:
            raise ValueError("Gamma API key not configured")

        input_text = (
            f"Қазақ тілінде {grade} оқушыларына арналған білім беру презентациясын жасаңыз.\n"
            f"Пән: {subject}\n"
            f"Тақырып: {topic}\n\n"
            f"Осы тақырыпты толық қамтитын, сынып деңгейіне сай түсінікті "
            f"түсініктемелері бар презентация жасаңыз. Барлық мәтін қазақ тілінде болуы керек."
        )

        payload = {
            "inputText": input_text,
            "textMode": "generate",
            "format": "presentation",
            "numCards": slides_count,
            "textOptions": {
                "amount": "medium",
                "language": "kk",
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GAMMA_BASE_URL}/generations",
                headers=self._headers(),
                json=payload,
            )

            if response.status_code not in (200, 201, 202):
                raise Exception(
                    f"Gamma API Error: {response.status_code} - {response.text}"
                )

            data = response.json()
            generation_id = data.get("generationId")
            if not generation_id:
                raise Exception(
                    f"Gamma API did not return generationId: {data}"
                )

            logger.info(f"Gamma generation started: {generation_id}")
            return generation_id

    async def check_generation_status(self, generation_id: str) -> dict:
        """
        Check the status of a Gamma generation.

        GET https://public-api.gamma.app/v1.0/generations/{generationId}

        Returns:
            dict with keys: generationId, status, gammaUrl (when completed), credits
        """
        if not self.api_key:
            raise ValueError("Gamma API key not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{GAMMA_BASE_URL}/generations/{generation_id}",
                headers=self._headers(),
            )

            if response.status_code == 404:
                raise Exception(f"Generation {generation_id} not found")
            if response.status_code not in (200, 202):
                raise Exception(
                    f"Gamma poll error: {response.status_code} - {response.text}"
                )

            return response.json()


# Create singleton instance
gamma_service = GammaService()
