def get(language):
    language = language.lower()
    if language == "english":
        return "en"
    elif language == "italiano":
        return "it"
    else:
        print("\n\n-------\nERROR, invalid language\n...... ")

        return
