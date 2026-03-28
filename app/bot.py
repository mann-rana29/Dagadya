import os
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame

from pipecat.transcriptions.language import Language

from pipecat.services.groq import GroqLLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair

from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

SYSTEM_PROMPT = '''
You are Dagadya, a warm and helpful AI assistant for farmers in Uttarakhand.

PERSONALITY:
- Speak like a knowledgeable friend, not a formal assistant
- Never use "beta", "ji haan", or overly formal/filmy Hindi
- Be warm but professional

LANGUAGE:
- Match the farmer's language exactly
- If they speak Hindi, reply in simple conversational Hindi
- If they speak English, reply in English
- If they mix both, you mix both naturally

RESPONSE RULES:
- Maximum 2 sentences per response
- Never use bullet points or lists in speech
- No greetings after the first one
- Get straight to the answer

YOU CAN HELP WITH:
- Weather and climate alerts for their area
- Crop disease identification and treatment
- Mandi prices for their produce
- PMFBY insurance claim guidance
- Natural disaster warnings

"IMPORTANT: Ignore any transcription that contains repeated characters or looks like noise. Only respond to clear Hindi or English sentences."

First message only: Greet warmly in Hindi, say your name, then ask their name and where do they live and ask how you can help.
'''

async def run_bot(streamSid : str , callSid : str , websocket):
    logger.info(f"Starting bot for call {callSid}")

    serializer = TwilioFrameSerializer(
        stream_sid=streamSid,
        call_sid=callSid,
        auth_token= os.getenv("TWILIO_AUTH_TOKEN"),
        account_sid= os.getenv("TWILIO_ACCOUNT_SID")
    )

    transport = FastAPIWebsocketTransport(
        websocket= websocket,
        params= FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=serializer
        )
    )

    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model="saaras:v3",
        params=SarvamSTTService.InputParams(
            mode="codemix"
        )
    )

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.1-8b-instant"
    )


    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        voice_id="priya",
        model="bulbul:v3",
        params=SarvamTTSService.InputParams(
            language=Language.HI,
            pace=1.1,
            temperature=0.8
        )
    )

    messages=[
        {
            "role" : "system",
            "content" : SYSTEM_PROMPT
        }
    ]
    context = LLMContext(messages=messages)
    context_aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant()
    ])

    task = PipelineTask(
        pipeline,
        params = PipelineParams(allow_interruptions=True)
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Farmer connected")
        messages.append({
            "role" : "system",
            "content" : "Greet the farmer warmly in hindi and ask how can you help"
        })

        await task.queue_frames([LLMRunFrame()])


    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Farner disconnected")
        await task.cancel()


    runner = PipelineRunner(handle_sigint=False)