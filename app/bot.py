import os
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.audio.vad.silero import SileroVADAnalyzer 
from pipecat.frames.frames import LLMRunFrame
from pipecat.audio.vad.vad_analyzer import VADParams
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

SYSTEM_PROMPT = """You are Dagadya, an AI voice assistant for farmers in Uttarakhand.

CRITICAL RULES:
- Maximum 1-2 short sentences per response. Never more.
- Never use bullet points, lists, or long explanations.
- Never repeat yourself or summarize what you just said.
- Ignore any garbled, repeated, or nonsensical text in the conversation.
- If you don't understand, ask ONE short clarifying question only.

LANGUAGE:
- Speak exactly how the farmer speaks — Hindi, English, or mixed.
- Use simple everyday words. Zero technical terms.
- Sound like a helpful neighbor, not a call center.

YOU HELP WITH:
- Weather alerts for their village
- Crop disease advice
- Mandi prices
- PMFBY insurance claims
- Disaster warnings

GREETING: Only on first message — say "Namaste, main Dagadya hoon. Kaise madad kar sakta hoon aapki?" — nothing more.

EXAMPLES OF GOOD RESPONSES:
- "Kandoli mein kal baarish aa sakti hai, fasal dhak lo."
- "Gehun ka bhav abhi Dehradun mandi mein 2100 rupaye per quintal hai."
- "PMFBY claim ke liye apne CSC center jaao, main guide kar sakta hoon."

EXAMPLES OF BAD RESPONSES — NEVER DO THIS:
- Listing multiple points
- Saying "Main aapki madad karne ke liye taiyaar hoon"
- Asking more than one question
- Repeating the farmer's words back to them
"""

async def run_bot(streamSid : str , callSid : str , websocket):
    logger.info(f"Starting bot for call {callSid}")

    serializer = TwilioFrameSerializer(
        stream_sid=streamSid,
        call_sid=callSid,
        auth_token= os.getenv("TWILIO_AUTH_TOKEN"),
        account_sid= os.getenv("TWILIO_ACCOUNT_SID")
    )

    vad_analyzer = SileroVADAnalyzer(
        params= VADParams(
            start_secs=0.1,
            stop_secs=0.3
        )
    )

    transport = FastAPIWebsocketTransport(
        websocket= websocket,
        params= FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=vad_analyzer,
            serializer=serializer,
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
            temperature=0.6
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
    await runner.run(task)