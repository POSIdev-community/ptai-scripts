# (c) Denis Danilov, https://swordfish-security.ru, 2024

import sys
import auth
from consts import URL


def get_users_with_projects() -> list[dict]:
    # Получаем полную инфу о пользователях с назначенными им проектами
    users = auth.requests_session.get(URL + "api/auth/membership")
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
        for project in user['projectMemberInfos']:
            # Заменяем каждый спецсимвол на экранированный
            project_name_sanitized = "".join(f"\\{char}" if char in regex_special_characters else char for char in project['projectName'])
            # И добавляем ^ и $ в начале и конце строки, чтобы регулярное выражение сработало только на полное совпадение
            output += f"{user['name']},{project['roleId']},^{project_name_sanitized}$\n"
    filename = "output.csv"
    if sys.argv[1]:
        filename = sys.argv[1]
    with open(filename, "w") as file:
        file.write(output)
    print("====== Файл сохранён! ======")


if __name__ == "__main__":
    main()