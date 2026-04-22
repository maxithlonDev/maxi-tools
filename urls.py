LOGIN_URL = "https://maxithlon.com/accesscontrol.php"
LOGOUT_URL = "https://maxithlon.com/logout.php"

ATHLETES_URL = "https://maxithlon.com/user/lista_atleti.php"


def get_athlete_details_url(user_id: int) -> str:
    return f"https://maxithlon.com/user/lista_atleti_altro.php?u={user_id}&t=all"
