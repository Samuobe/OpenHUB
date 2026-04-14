def get(language):
    language = language.lower()
    if language == "english":
        return "en"
    elif language == "italiano":
        return "it"
    else:
        print("\n\n-------\nERROR, invalid language, using English. Report this on the GitHub repo (https://github.com/Samuobe/OpenHUB) so we can add your language as soon as possible!\n...... ")

        return "en"
