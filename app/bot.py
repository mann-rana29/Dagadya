import os
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame, TextFrame
from pipecat.processors.frame_processor import FrameProcessor

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
from agent_router import route_query

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

AGENT INFORMATION:
- You have access to real-time weather data for weather queries
- You have access to mandi prices for crop market queries
- You have insurance guidance for PMFBY and crop insurance queries
- When you receive [AGENT RESPONSE] messages, incorporate that data into your response naturally

"IMPORTANT: Ignore any transcription that contains repeated characters or looks like noise. Only respond to clear Hindi or English sentences."

First message only: Greet warmly in Hindi, say your name, then ask their name and where do they live and ask how you can help.
'''


class AgentRouterProcessor(FrameProcessor):
    """
    Custom frame processor that routes user queries through the agent router
    and formats responses back to the pipeline
    """
    
    def __init__(self):
        super().__init__()
    
    async def process_frame(self, frame):
        """Process incoming frames and route queries"""
        try:
            # Handle text frames (transcribed user messages)
            if isinstance(frame, TextFrame):
                user_text = frame.text
                logger.info(f"User query: {user_text}")
                
                if not user_text or len(user_text.strip()) < 2:
                    await self.push_frame(frame)
                    return
                
                # Route the query through agent router
                result = route_query(user_text)
                message = result.get("message", "")
                
                logger.info(f"Router response: {message}")
                
                # Push the routed response as a system message for LLM context
                system_msg = TextFrame(f"[AGENT RESPONSE] {message}")
                await self.push_frame(system_msg)
        
        except Exception as e:
            logger.error(f"Error in AgentRouterProcessor: {e}")
        
        # Always push the frame down the pipeline
        await self.push_frame(frame)


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

    # Initialize agent router processor
    agent_router = AgentRouterProcessor()

    pipeline = Pipeline([
        transport.input(),
        stt,
        agent_router,
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