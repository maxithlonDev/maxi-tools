LOGIN_URL = "https://www.maxithlon.com/accesscontrol.php"
ATHLETES_URL = "https://www.maxithlon.com/user/lista_atleti.php"


def get_athlete_details_url(user_id: int) -> str:
    return f"https://www.maxithlon.com/user/lista_atleti_altro.php?u={user_id}&t=all"
