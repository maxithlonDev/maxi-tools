import requests
import urls as url_utils


def login(username: str, password: str):
    session = requests.Session()

    payload = {
        "user": username,
        "password": password,
        "id_gioco": "1",
        "indir": "/",
        "user_control": "Login",
    }

    resp = session.post(url_utils.LOGIN_URL, data=payload)
    resp.raise_for_status()

    return session, resp.text
