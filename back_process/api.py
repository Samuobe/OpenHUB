import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import FastAPI
import uvicorn
from Lattuga.lattuga import manual_input
from functions.notify import system_notification

app = FastAPI()

@app.get("/ping")
async def send_ping():
    return {"Message": "Pong!"}

@app.get("/prompt")
def prompt(prompt: str, device_name: str):
    try:
        response = manual_input(prompt+". Reply without sgined text like bold and emoji. This request is from: "+device_name)
        return {"Response": response}
    except:
        return {"Response": "ERROR: Error during ask AI"}
        

@app.get("/notify")
def notify(title: str, content: str):
    try:
        system_notification(title, content)
        return {"Response": "Notify sent correctly"}
    except:
        return {"Response": "ERROR: Error during sending notify"}
        
        
    


uvicorn.run(app, host="0.0.0.0", port=8000)