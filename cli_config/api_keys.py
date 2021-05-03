API_KEYS = {
    "RED": "12345",
    "OPS": "678910"
}


def get_key(id):
    if id == "RED":
        return API_KEYS[id]
    elif id == "OPS":
        return f"token {API_KEYS[id]}"
