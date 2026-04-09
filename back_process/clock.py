import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import glob
import datetime
import threading
import time
from functions.notify import music_advice
import functions.lpak as lpak

clock_file = "operations_data/clock.txt"

already_used=[]
def start_timer(name, time, tipe, stot, base):
    os.system("sleep "+str(stot))

    if "playing" in str(os.popen("playerctl status").read()).lower():
        music = True
    if music == True:
        os.system("playerctl pause")

    advice_text=f"{name} {lpak.get("Terminated", language).lower()}!"
    alert_thread = threading.Thread(target=music_advice, args=(advice_text,))
    alert_thread.start()
    alert_thread.join() 


    if music == True:
        os.system("playerctl play")

    with open(clock_file, "r") as f:
        data = f.readlines()
    
    with open(clock_file, "w") as f:
        for timer in data:
            if timer != base:
                f.write(timer)
    
    
  
    


def main():
    global clock_file, already_used
    now = datetime.datetime.now()
    try:
        with open(clock_file, "r") as f:
            clock_data = f.readlines()
    except:
        return
    
    now = str(now)
    time = now.split(" ")[1].split(".")[0]
    h1,m1,s1=time.split(":")
    for data in clock_data:
        try:
            if not data in already_used:
                already_used.append(data)
                event_name=data.split("|")[0]
                event_time = data.split("|")[1]
                h2,m2,s2 = event_time.split(":")
                event_tipe = data.split("|")[2]

                s1 = int(s1)
                m1 = int(m1) 
                h1 = int(h1)
                s2 = int(s2)
                m2 = int(m2)
                h2 = int(h2)

                ss=s2-s1
                ms=m2-m1
                hs=h2-h1

                stot = ss+ms*60+hs*60*60
                print("STOT= ",stot)
                if stot > 0:                    
                    thread1 = threading.Thread(target=start_timer, args=(event_name, event_time, event_time, stot, data ))
                    thread1.start()
        except:
            pass
    
    
while True:
    main() 
    os.system("sleep 1") 
