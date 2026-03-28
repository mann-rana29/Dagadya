from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
import json
from bot import run_bot
from twilio.rest import Client
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class CallRequest(BaseModel):
    phone_number : str

@app.get("/")
async def root():
    return HTMLResponse(content="""
        <Response>
            <Connect>
                <Stream url="wss://dagadya-production.up.railway.app/ws"/>
            </Connect>
        </Response>
    """, media_type="application/xml")

@app.post("/")
async def root_post():
    return HTMLResponse(content="""
        <Response>
            <Connect>
                <Stream url="wss://dagadya-production.up.railway.app/ws"/>
            </Connect>
        </Response>
    """, media_type="application/xml")

@app.get("/ui")
async def ui():
    return FileResponse("index.html")

@app.get("/playback")
async def playback():
    return FileResponse("playback.html")

@app.get("/audio")
async def audio():
    """Serve the recording audio file"""
    audio_path = "recordings/demo.mpeg"
    if not os.path.exists(audio_path):
        return {"error": "Recording not found. Place your audio.mpeg file at recordings/demo.mpeg"}, 404
    return FileResponse(audio_path, media_type="audio/mpeg")

@app.websocket("/ws")
async def websocket(websocket : WebSocket):
    await websocket.accept()

    data = await websocket.receive_text()
    message = json.loads(data)

    if message.get("event") == "connected":
        data = await websocket.receive_text()
        message = json.loads(data)

    stream_sid = message["start"]["streamSid"]
    call_sid = message["start"]["callSid"]
    
    await run_bot(stream_sid,call_sid , websocket)

@app.post("/call")
async def make_call(request : CallRequest):
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )

    call= client.calls.create(
        to = request.phone_number,
        from_= os.getenv("TWILIO_PHONE_NUMBER"),
        url="https://dagadya-production.up.railway.app/"
    )

    return {"status" : "calling", "sid" : call.sid}
