# (c) Denis Danilov, https://swordfish-security.ru, 2025

import argparse
import csv
import re
import sys
from auth import Authenticator
from consts import URL

# Создание парсера аргументов командной строки
parser = argparse.ArgumentParser(
    description='Скрипт для назначения ролей в проектах PTAI на основе регулярных выражений', add_help=False, epilog="")
parser.add_argument('-h', '--help', action='help', help='показать данную справку и выйти')
parser.add_argument('--regcheck', action='store_true',
                    help='вывести список проектов, попадающих под регулярные выражения из csv файла')
parser.add_argument('--insecure', action='store_true',
                    help='отключить проверку SSL-сертификатов')
parser.add_argument('filename', type=str, help='имя CSV файла с данными')
parser._positionals.title = "Позиционные аргументы"
parser._optionals.title = "Опции"
args = parser.parse_args()

ptai = Authenticator(URL, args.insecure)

# Проверка подключения к PTAI. Если подключение прошло неудачно, завершаем работу
if not ptai.connected():
    sys.exit(1)

# Аутентификация пользователя
try:
    ptai.do_auth()
except Exception as e:
    print(e)
    sys.exit(1)

# Словарь для удобного хранения данных о пользователях и их ролях, плюс группировка
# { Имя: { регулярка: роль; регулярка2: роль }
user_role_data: dict[str, dict[str, str]] = dict()

# Парсинг CSV файла и заполнение словаря user_role_data
with open(args.filename, encoding='utf-8') as input_csv:
    csv_reader = csv.reader(input_csv)
    next(csv_reader)
    for row in csv_reader:
        username, role_name, regex_pattern = map(str.strip, row)
        if username not in user_role_data:
            user_role_data[username] = {}
        user_role_data[username][regex_pattern] = role_name

print("====== Получение списка проектов ======")
projects_raw = ptai.session.get(URL + "api/projects").json()
projects_name = {project_object['id']: project_object['name'] for project_object in projects_raw}
print("====== Список проектов получен успешно ======")

# Проверка регулярных выражений из CSV файла
if args.regcheck:
    with open(args.filename) as input_csv:
        csv_reader = csv.reader(input_csv)
        next(csv_reader)
        for row in csv_reader:
            username, role_id, regex_pattern = map(str.strip, row)
            regex_pattern_compiled = re.compile(regex_pattern)
            matching_projects = [
                project_name
                for project_id, project_name in projects_name.items()
                if regex_pattern_compiled.match(project_name)
            ]
            print(f"{regex_pattern}: {', '.join(matching_projects)}")
    sys.exit(0)

# Получение списка пользователей
print("====== Получение списка пользователей ======")
users = ptai.session.get(URL + "api/auth/membership").json()
print("====== Список пользователей получен успешно ======")

def first(iterable, default=None):
    for item in iterable:
        return item
    return default

# Словарь пользователей по имени для быстрого доступа
users_by_name = {user['name']: user for user in users}

# Словарь для хранения измененных проектов пользователей
user_modified_projects: dict[str, list] = dict()

# Создание массива существующих ролей для дальнейшей проверки
roles_raw = ptai.session.get(URL + "api/auth/roles").json()
valid_roles = {role['name'] for role in roles_raw}

# Финальный массив из запросов, которые будут отправляться в PT AI
user_requests = []

# Перебор пользователей и их ролей
for username, regex_and_role_data in user_role_data.items():
    if username not in [user_obj['name'] for user_obj in users]:
        print(f"WARN: Пользователь {username} не найден!")
        continue

    user_id = users_by_name[username]['id']

    # Словарь из ролей, содержащих в себе список проектов
    # Нужен, чтобы в рамках одного пользователя сгруппировать роли
    # { роль: { имя_роли: "имя_роли", ... , проекты: [ список_проектов ] } }
    role_set: dict[str, dict[str, str | bool | list[dict]]] = dict()
    # Поскольку нам нужно сделать соответствие роль -> список проектов, сначала проходимся по ролям.
    for regex_pattern, role_name in regex_and_role_data.items():
        if role_name not in valid_roles:
            print(f"WARN: У пользователя {username} указана некорректная роль {role_name}")
            continue

        # После проверки того, что эта роль вообще существует, составляем список проектов, которые подходят под регулярку
        pattern = re.compile(regex_pattern)
        matching_projects = [
            {"id": project_id, "name": project_name}
            for project_id, project_name in projects_name.items()
            if pattern.match(project_name)
        ]

        # Если роль в словаре уже существует, значит есть и список проектов. Добавляем найденные проекты в него
        # В ином случае, создаём эту роль и сразу заполняем список найденными проектами
        role_set.setdefault(role_name, {
            "name": role_name,
            "autoSet": False,
            "allProjects": False,
            "projects": []
        })['projects'].extend(matching_projects)

    user_requests.append({
        "id": user_id,
        "roles": list(role_set.values())
    })

# Вывод новых проектных ролей для пользователей
print("====== Новые проектные роли для пользователей ======")
for user in user_requests:
    print(f"## {first(user_print['name'] for user_print in users if user_print['id'] == user['id'])}")
    for role in user['roles']:
        print(f"{role['name']}: {', '.join([project['name'] for project in role['projects']])}")
    print('\n')

print("Внимание! Если пользователь не указан в списке, у него удалятся все роли, не назначенные автоматически!\n" +
      "Если вы хотите только добавить новые роли, но оставить все старые, вставьте вывод скрипта export_project_roles.py в csv-файл.")
print("Изменить? [y/N]")

if input().lower() not in ['y', 'yes', 'д', 'да']:
    print("Отмена операции, изменения не будут применены")
    sys.exit(0)

# Отправка всех запросов на сервер PT AI.
# Поскольку PT AI в запросе PUT принимает один объект, а не массив из объектов, нужно каждый запрос посылать отдельно
for user_object in user_requests:
    req = ptai.session.put(URL + "api/auth/membership", json=user_object)
    if not req.ok:
        print(f"ERR: Ошибка при изменении проектов пользователя {user_object['id']}. Сервер вернул код {req.status_code}")
        print(f"Ответ от сервера: {req.json()}")

print("Загрузка завершена успешно!")