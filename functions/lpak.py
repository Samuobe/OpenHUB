def get(word, language):
    
    line_found = []

    with open(f"lpak/{language}.lpak", "r") as file:        
        for line in file:
            
            try:
                parts = line.split("|", 1)              
                    
                key, value = parts[0].strip(), parts[1].strip() 
            except:
                continue               
              
            if key == word:
                return str(value)
    if language != "English":
        print(f"&&&TRADUCTION NOT FOUND, USING ENGLISH: {word}")
        with open(f"lpak/English.lpak", "r") as file:
            for line in file:
                try:
                    parts = line.split("|", 1)              
                        
                    key, value = parts[0].strip(), parts[1].strip() 
                except:
                    continue                
                    
                if key == word:
                    return str(value) 
    print(f"&&&&&TRANSLATION MISSING: {word}")               
    return word