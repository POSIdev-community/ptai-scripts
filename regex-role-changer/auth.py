# (c) Denis Danilov, https://swordfish-security.ru, 2025

import requests
import urllib3
import pwinput
from consts import LOGIN, PASSWORD

class Authenticator:
    def __init__(self, url, insecure=False):
        self.url = url
        self.session = requests.Session()
        self.session.verify = not insecure

    def do_auth(self) -> None:
        access_token = self.get_bearer_token()
        self.session.headers["Authorization"] = "Bearer " + access_token

    def connected(self) -> bool:
        try:
            self.session.get(self.url + "health/summary")
            return True
        except urllib3.exceptions.NameResolutionError as e:
            print("ERR: Неверный URL. Проверьте правильность ввода и наличие подключения к интернету или VPN (если требуется)")
            print(f"Информация: {e}")
        except Exception as e:
            print("ERR: Произошла ошибка при подключении. Проверьте правильность ввода и наличие подключения к интернету или VPN (если требуется)")
            print(f"Информация: {e}")
        return False

    def get_bearer_token(self) -> str:
        login = LOGIN or input("Введите логин пользователя: ")
        password = PASSWORD or pwinput.pwinput("Введите пароль: ")

        res = self.session.post(self.url + "api/auth/userLogin?scopeType=Web", json={
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
