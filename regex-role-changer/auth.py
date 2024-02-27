# (c) Denis Danilov, https://swordfish-security.ru, 2024

import requests
import urllib3
import pwinput

from consts import URL, LOGIN, PASSWORD

requests_session = requests.Session()

def do_auth() -> None:
    access_token = get_bearer_token()
    requests_session.headers["Authorization"] = "Bearer " + access_token


def connected() -> bool:
    try:
        # Нам подойдёт любой status_code, главное, что сервер отвечает
        requests.get(URL + "health/summary")
        return True
    except urllib3.exceptions.NameResolutionError as e:
        print("ERR: Неверный URL. Проверьте правильность ввода и наличие подключения к интернету или VPN (если требуется)")
        print(f"Информация: {e}")
    except Exception as e:
        print("ERR: Произошла ошибка при подключении. Проверьте правильность ввода и наличие подключения к интернету или VPN (если требуется)")
        print(f"Информация: {e}")
    return False


def get_bearer_token() -> str:
    login = LOGIN or input("Введите логин пользователя: ")
    password = PASSWORD or pwinput.pwinput("Введите пароль: ")
    
    res = requests.post(URL + "api/auth/userLogin?scopeType=Web", json={
        "login": login,
        "password": password,
        "rememberMe": False
    },
    headers={
        "Content-Type": "application/json-patch+json",
    })
    if res.status_code == 200:
        json = res.json()
        print("\n====== Подключение прошло успешно ======\n")
        return json["accessToken"]
    elif res.status_code == 400:
        raise Exception(f"ERR: Некорректный запрос. Информация от сервера: {res.json()}")
    elif res.status_code == 401:
        raise Exception("ERR: Не удалось подключиться к серверу. Неверный логин или пароль")
    else:
        raise Exception(f"ERR: Произошла неизвестная ошибка. Сервер вернул код {res.status_code}. Информация от сервера: {res.json()}")
