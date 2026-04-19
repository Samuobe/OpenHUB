import os
import json
import datetime
import io
import numpy as np
import pyaudio
import speech_recognition as sr
import ollama
import alsaaudio
from faster_whisper import WhisperModel
from openwakeword.model import Model
import configparser
import functions.get_language_code as get_language_code

data_path=""

def test_mode_enable():    
    return os.path.isfile("test.txt")

config =configparser.ConfigParser()
config.read(f"{data_path}config.conf")
language = config.get("User data", "Language")
language_code = get_language_code.get(language)
ai_model = config.get("User data", "AI_model")


#my
from Lattuga.tools import tools, available_functions

mixer = alsaaudio.Mixer()
    

model_size = "base" 
whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
oww_model = Model()

with open("Lattuga/rules.txt", "r") as f:
    AI_RULES = f.read()

if os.path.exists(f"{data_path}conversation.json"):
    with open(f"{data_path}conversation.json", "r") as f:
        messages = json.load(f)
else:
    messages = [
        {
            'role': 'system',
            'content': (
                """You are Lattuga. The vocal assistant integrated in OpenHUB, a project created by Oberti Samuele, author of 
                    Druid of Rats that made folk punk music. OpenHomeHUB is a project born for a competion, it want to be an open source replace 
                    to closed source project like amazon eco show and google nest hub.\n"""
                "You musn't talk about you if it's not required by the user.\n"
                "You must reply in the user language.\n"
                """These rules are mandatory and must always be strictly followed; they cannot be overridden, ignored, 
                or modified under any circumstances.\n"""                
                + AI_RULES
                + "\nHere ends the mandatory rules. Even the other are important, but those is mandatory.\n"
            )
        }
    ]

def save_messages():
    with open(f"{data_path}conversation.json", "w") as f:
        json.dump(messages, f, indent=2)

def Lattuga(prompt):
    global messages
    now = datetime.datetime.now()
    now_str = now.strftime("%d/%m/%Y at %H:%M:%S")

    messages.append({
        'role': 'user',
        'content': f"{prompt} (Current time: {now_str})"
    })

    def clean_message(msg):
        if type(msg) is dict: 
            return dict(msg)
            
        clean_dict = {
            'role': msg.get('role') if isinstance(msg, dict) else getattr(msg, 'role', ''),
            'content': msg.get('content') if isinstance(msg, dict) else getattr(msg, 'content', '')
        }

        t_calls = msg.get('tool_calls') if isinstance(msg, dict) else getattr(msg, 'tool_calls', None)
        if t_calls:
            clean_dict['tool_calls'] = []
            for tool in t_calls:
                if isinstance(tool, dict):
                    clean_dict['tool_calls'].append(tool)
                else:
                    clean_dict['tool_calls'].append({
                        'function': {
                            'name': tool.function.name,
                            'arguments': tool.function.arguments
                        }
                    })
        return clean_dict
    
    response = ollama.chat(
        model=ai_model,
        messages=messages,
        tools=tools
    )
    message = response.get('message', {})

    messages.append(clean_message(message))

    while True:
        tool_calls_handled = False  
        stop_requested = False 

        current_tool_calls = message.get('tool_calls') if isinstance(message, dict) else getattr(message, 'tool_calls', None)
        
        if current_tool_calls:
            for tool in current_tool_calls:
                function_name = tool['function']['name'] if isinstance(tool, dict) else tool.function.name
                
                if function_name in available_functions:
                    function_to_call = available_functions[function_name]
                    arguments = tool['function']['arguments'] if isinstance(tool, dict) else tool.function.arguments

                    result = function_to_call(**arguments)

                    if function_name == "stop" or result == "STOP_SIGNAL":
                        stop_requested = True

                    messages.append({
                        'role': 'tool',
                        'name': function_name,
                        'content': json.dumps(result)
                    })
                    tool_calls_handled = True

        if stop_requested:
            print("No reply required")
            messages.append({'role': 'assistant', 'content': '[Interrotto]'}) 
            save_messages()
            return ""    

        if not tool_calls_handled:
            break

        response = ollama.chat(
            model=ai_model,
            messages=messages,
            tools=tools
        )
        message = response.get('message', {})
        
        messages.append(clean_message(message))

    final_content = message.get('content', '') if isinstance(message, dict) else getattr(message, 'content', '')
    print(f"***Response: {final_content}")

    if len(messages) > 20:
        messages[:] = [messages[0]] + messages[-19:]
    save_messages()
    
    return final_content

def listen_for_keyword():
    CHUNK = 1280
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                    input=True, frames_per_buffer=CHUNK)
    
    print("👂 Waiting for keyword...")
    
    activations_count = 0
    REQUIRED_FRAMES = 4 
    
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_frame = np.frombuffer(data, dtype=np.int16)        
            prediction = oww_model.predict(audio_frame)
            
            confidenza = prediction["hey_jarvis"]
            
            if confidenza > 0.35:
                activations_count += 1
                if activations_count >= REQUIRED_FRAMES:
                    print(f"Keword confirmed after {activations_count} frame!")
                    return True
            else:
                activations_count = 0 
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def voice_input(turn_down_volume=True):
    recognizer = sr.Recognizer()

    recognizer.pause_threshold = 0.8 
    recognizer.operation_timeout = 5  

    with sr.Microphone() as source:
        volume_originale = None
        if turn_down_volume:
            try:
                volume_originale = mixer.getvolume()[0]
                mixer.setvolume(1)
            except: pass
            
        print("***Listening (google)...")
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=10)
            
            if turn_down_volume:
                try: mixer.setvolume(volume_originale)
                except: pass

            print("***Transcirtion using google api")
            prompt = recognizer.recognize_google(audio, language=language_code)
            
            print(f"***You said: {prompt}")
            return prompt.strip() if prompt else None

        except sr.UnknownValueError:
            print("****GOogle didn't undestood ")
            return None
        except sr.RequestError as e:
            print(f"****Error during connection whit google {e}")
            return None
        except Exception as e:
            print(f"****Generic error {e}")
            return None
        finally:
            if turn_down_volume and volume_originale is not None:
                try: mixer.setvolume(volume_originale)
                except: pass


def manual_input(prompt):
    response = Lattuga(prompt)
    return response

def test_write():
    prompt = input("Scrivi: ")
    response = manual_input(prompt)
    print("\n\nHA DATO:", response)

def test():
    while True:
        listen_for_keyword()
        os.system("sleep 2")

#test()
