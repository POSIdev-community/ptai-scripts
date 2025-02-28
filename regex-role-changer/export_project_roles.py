# (c) Denis Danilov, https://swordfish-security.ru, 2025

import sys
from auth import Authenticator
from consts import URL

auth = Authenticator(URL)

def get_users_with_projects() -> list[dict]:
    # Получаем полную инфу о пользователях с назначенными им проектами
    users = auth.session.get(URL + "api/auth/membership")
    if users.status_code != 200:
        raise Exception(f"Произошла ошибка при запросе к серверу. Status Code: {users.status_code}\n{users.text}")
    users = users.json()
    return users


def main():
    if not auth.connected():
        return
    auth.do_auth()
    users = get_users_with_projects()
    regex_special_characters = ".^$*+?{}[]\\|()"
    output = ""
    for user in users:
        for role in user['roles']:
            for project in role['projects']:
                # Заменяем каждый спецсимвол на экранированный
                project_name_sanitized = "".join(f"\\{char}" if char in regex_special_characters else char for char in project['name'])
                # И добавляем ^ и $ в начале и конце строки, чтобы регулярное выражение сработало только на полное совпадение
                output += f"{user['name']},{role['name']},^{project_name_sanitized}$\n"
    filename = "output.csv"
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    with open(filename, "w", encoding='utf-8') as file:
        file.write(output)
    print("====== Файл сохранён! ======")


if __name__ == "__main__":
    main()
