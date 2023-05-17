import io
import logging
from typing import Any, Optional
import aiohttp
from pydub import AudioSegment

from vocode import getenv
from vocode.streaming.synthesizer.base_synthesizer import (
    BaseSynthesizer,
    SynthesisResult,
)
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from vocode.streaming.agent.bot_sentiment_analyser import BotSentiment
from vocode.streaming.models.message import BaseMessage


ADAM_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
ELEVEN_LABS_BASE_URL = "https://api.elevenlabs.io/v1/"


class ElevenLabsSynthesizer(BaseSynthesizer):
    def __init__(
        self,
        config: ElevenLabsSynthesizerConfig,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(config)

        import elevenlabs

        self.elevenlabs = elevenlabs

        self.api_key = config.api_key or getenv("ELEVEN_LABS_API_KEY")
        self.voice_id = config.voice_id or ADAM_VOICE_ID
        self.stability = config.stability
        self.similarity_boost = config.similarity_boost
        self.words_per_minute = 150

    async def create_speech(
        self,
        message: BaseMessage,
        chunk_size: int,
        bot_sentiment: Optional[BotSentiment] = None,
    ) -> SynthesisResult:
        voice = self.elevenlabs.Voice(voice_id=self.voice_id)
        if self.stability is not None and self.similarity_boost is not None:
            voice.settings = self.elevenlabs.VoiceSettings(
                stability=self.stability, similarity_boost=self.similarity_boost
            )
        url = ELEVEN_LABS_BASE_URL + f"text-to-speech/{self.voice_id}"
        headers = {"xi-api-key": self.api_key}
        body = {
            "text": message.text,
            "voice_settings": voice.settings.dict() if voice.settings else None,
        }

        async with aiohttp.ClientSession() as session:
            async with session.request(
                "POST",
                url,
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if not response.ok:
                    raise Exception(
                        f"ElevenLabs API returned {response.status} status code"
                    )
                audio_data = await response.read()
                audio_segment: AudioSegment = AudioSegment.from_mp3(
                    io.BytesIO(audio_data)
                )

                output_bytes_io = io.BytesIO()

                audio_segment.export(output_bytes_io, format="wav")

                return self.create_synthesis_result_from_wav(
                    file=output_bytes_io,
                    message=message,
                    chunk_size=chunk_size,
                )
