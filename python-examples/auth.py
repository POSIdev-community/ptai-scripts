# PT AI authentication via AccessToken

import requests

BASE_URL = "https://ai-server.example.com/"
# You can obtain the token via Settings in the WEB UI
ACCESS_TOKEN = "IZdrBx4LRcTiy0mWJvLK0XS/MEVDDSd8"


requests_session = requests.Session()


def auth() -> None:
    access_token = get_bearer_token()

    # do not forget to add 'Bearer ' before a token!
    requests_session.headers["Authorization"] = "Bearer " + access_token


def get_bearer_token() -> str:
    res = requests_session.get(
        url=BASE_URL + "api/auth/signin?scopeType=AccessToken",
        headers={"Access-Token": ACCESS_TOKEN}
    )
    json = res.json()

    access_token = json["accessToken"]
    refresh_token = json["refreshToken"]
    expired_at = json["expiredAt"]

    print("access_token="+access_token)
    print("refresh_token="+refresh_token)
    print("expiredAt="+expired_at)

    return access_token


def get_all_projects() -> list[dict[str, any]]:
    res = requests_session.get(BASE_URL + "api/projects")
    json = res.json()

    return json


def main():
    # disable SSL check
    requests_session.verify = False

    # set the obtained token to the header 'Authorization' for the session
    auth()

    # let's do something with the token!
    projects = get_all_projects()
    for project in projects:
        print("id = %s" % project["id"])
        print("name = %s" % project["name"])
        print("creationDate = %s" % project["creationDate"])
        print("settingsId = %s" % project["settingsId"])


if __name__ == "__main__":
    main()
