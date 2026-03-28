import os
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.network.websocket_server import WebsocketServerTransport , WebsocketServerParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame

from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair



from dotenv import load_dotenv
from loguru import logger

load_dotenv()

SYSTEM_PROMPT = '''
                    Aap Dagadya hain — Uttarakhand ke kisanon ke liye ek AI sahayak.
                    Aapka naam Garhwali/Pahadi mein "dost" ya "saathi" ka matlab hai.
                    Aap Hindi aur English dono mein baat kar sakte hain — jis bhasha mein
                    kisan bole, usi mein jawab do.

                    Aap yeh kar sakte hain:
                    - Mausam ki jaankari dena
                    - Mandi prices batana
                    - PMFBY insurance claim mein madad karna
                    - Fasal ki beemari ke baare mein salah dena
                    - Prakritik aapda ke baare mein alert dena

                    Hamesha chhote aur simple jawab do — 2 ya 3 sentences maximum.
                    Kisan ki baat dhyan se suno aur seedha jawab do.
                    Koi bhi technical jargon mat use karo.
                '''


async def run_bot(streamSid : str , callSid : str , websocket):
    logger.info(f"Starting bot for call {callSid}")

    serializer = TwilioFrameSerializer(
        stream_sid=streamSid,
        call_sid=callSid,
        auth_token= os.getenv("TWILIO_AUTH_TOKEN"),
        account_sid= os.getenv("TWILIO_ACCOUNT_SID")
    )

    transport = WebsocketServerTransport(
        websocket = websocket,
        params=WebsocketServerParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer= SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=serializer
        )
    )

    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model="saarika:v2",
        language="hi-IN"
    )

    llm = GoogleLLMService(
        api_key=os.getenv("GEMINI_API_KEY"),
        model="gemini-2.0-flash"
    )

    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY"),
        model="bulbul:v3",
        speaker="anushka",
        target_language_code="hi-IN"
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
        PipelineParams(allow_interruptions=True)
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