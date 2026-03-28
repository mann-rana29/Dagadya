import os
from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.daily.transport import DailyParams

from pipecat.services.google.llm import GoogleLLMService
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.network.websocket_server import WebsocketServerTransport

load_dotenv(override=True)



async def bot(runner_args: RunnerArguments):
    """Main bot entry point."""
    
    # Create transport (supports both Daily and WebRTC)
    transport = await create_transport(
        runner_args,
        {
            "daily": lambda: DailyParams(audio_in_enabled=True, audio_out_enabled=True),
            "webrtc": lambda: TransportParams(
                audio_in_enabled=True, audio_out_enabled=True
            ),
        },
    )




    # Initialize AI services
    stt = SarvamSTTService(api_key=os.getenv("SARVAM_API_KEY"))
    tts = SarvamTTSService(api_key=os.getenv("SARVAM_API_KEY"))
    llm = GoogleLLMService(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")

    # Set up conversation context
    messages = [
        {
            "role": "system",
            "content": '''Aap Dagadya hain — Uttarakhand ke kisanon ke liye ek AI sahayak.
        Aap Hindi aur English dono mein baat kar sakte hain.
        
        Aap yeh kar sakte hain:
        - Mausam ki jaankari dena (Open-Meteo API se)
        - Mandi prices batana (Agmarknet se)
        - PMFBY insurance claim mein madad karna
        - Fasal ki beemari ke baare mein salah dena
        
        Hamesha chhote aur simple jawab do.
        Farmer ki baat dhyan se suno.''',
        },
    ]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    # Build pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(pipeline)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        messages.append(
            {"role": "system", "content": "Say hello and briefly introduce yourself."}
        )
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
