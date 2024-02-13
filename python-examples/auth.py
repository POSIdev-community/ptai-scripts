import requests

from consts import ACCESS_TOKEN, BASE_URL

requests_session = requests.Session()


def do_auth() -> None:
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


def main():
    # disable SSL check
    requests_session.verify = False

    # set the obtained token to the header 'Authorization' for the session
    do_auth()


if __name__ == "__main__":
    main()
