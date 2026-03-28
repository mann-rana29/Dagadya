from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
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
                <Stream url="wss://dagadya.railway.app/ws"/>
            </Connect>
        </Response>
    """, media_type="application/xml")

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
        url="https://dagadya.railway.app/"
    )

    return {"status" : "calling", "sid" : call.sid}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000 , reload=True)