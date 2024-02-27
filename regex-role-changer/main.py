# (c) Denis Danilov, https://swordfish-security.ru, 2024

import argparse
import csv
import re
import sys
import auth
from consts import URL

# Создание парсера аргументов командной строки
parser = argparse.ArgumentParser(description='Скрипт для назначения ролей в проектах PTAI на основе регулярных выражений', add_help=False,
                                 epilog="")
parser.add_argument('-h', '--help', action='help', help='показать данную справку и выйти')
parser.add_argument('--regcheck', action='store_true', help='вывести список проектов, попадающих под регулярные выражения из csv файла')
parser.add_argument('filename', type=str, help='имя CSV файла с данными')
parser._positionals.title = "Позиционные аргументы"
parser._optionals.title = "Опции"
args = parser.parse_args()

# Проверка подключения к PTAI. Если подключение прошло неудачно, завершаем работу
if not auth.connected():
    sys.exit(1)

# Аутентификация пользователя
try:
    auth.do_auth()
except Exception as e:
    print(e)
    sys.exit(1)

# Получение списка проектов
projects_raw = auth.requests_session.get(URL + "api/projects")
projects_raw = projects_raw.json()
projects_name = [project_object['name'] for project_object in projects_raw]

# Проверка регулярных выражений из CSV файла
if args.regcheck:
    with open(args.filename) as input_csv:
        csv_reader = csv.reader(input_csv)
        next(csv_reader)
        for row in csv_reader:
            username, role_id, regex_pattern = map(str.strip, row)
            regex_pattern_compiled = re.compile(regex_pattern)
            matching_projects = list(filter(regex_pattern_compiled.match, projects_name))
            print(f"{regex_pattern}: {', '.join(matching_projects)}")
    sys.exit(0)

# Получение списка пользователей
users = auth.requests_session.get(URL + "api/auth/membership")
users = users.json()

# Генерация уникального идентификатора связки пользователь-проект, чтобы избежать конфликтов
# Используется при появлении у пользователя новой роли на проекте, где он не был назначен
max_id = max(project['id'] for user_info in users for project in user_info["projectMemberInfos"])

def increment_and_return_id() -> int:
    global max_id
    max_id += 1
    return max_id

def first(iterable, default=None):
  for item in iterable:
    return item
  return default

def roleid_to_name(role_id: int) -> str:
    return {
        2: "Аудитор",
        3: "Менеджер безопасности",
        5: "Разработчик"
    }.get(role_id, "Никто")

# Словарь для удобного хранения данных о пользователях и их ролях, плюс группировка
# { Имя: { регулярка: роль; регулярка2: роль }
user_role_data: dict[str, dict[str, int]] = dict()

# Парсинг CSV файла и заполнение словаря user_role_data
with open(args.filename) as input_csv:
    csv_reader = csv.reader(input_csv)
    next(csv_reader)
    for row in csv_reader:
        username, role_id, regex_pattern = map(str.strip, row)
        if username not in user_role_data:
            user_role_data[username] = {}
        user_role_data[username][regex_pattern] = int(role_id)

# Словарь для хранения новых ролей
new_roles: dict[str, list] = dict()

# Список с проектами и пользователями, которые были изменены. Необходимо для трекинга изменений
changed_project_ids: list[int] = []
changed_user_names: list[str] = []

# Словарь для хранения измененных проектов пользователей
user_modified_projects: dict[str, list] = dict()

# Перебор пользователей и их ролей
for username, regex_and_role_data in user_role_data.items():
    if username not in [user_obj['name'] for user_obj in users]:
        print(f"WARN: Пользователь {username} не найден!")
        continue
    for regex_pattern, role_id in regex_and_role_data.items():
        if role_id not in (2, 3, 5):
            print(f"WARN: У пользователя {username} указана некорректная роль {role_id}")
            continue
        regex_pattern_compiled = re.compile(regex_pattern)
        
        matching_projects = list(filter(regex_pattern_compiled.match, projects_name))
        for project_name in matching_projects:
            # Пробуем найти уже существующие назначения на роли. Если они есть, то модифицируем их
            modified_user_projects = []
            created_user_projects = []
            for idx, user_project in enumerate(users):
                if user_project['name'] != username:
                    continue
                try:
                    project_index = [proj['projectName'] for proj in user_project['projectMemberInfos']].index(project_name)
                    modified_user_project = users[idx]['projectMemberInfos']
                    # Даже если проектные роли совпадают, их нужно добавить в запрос, иначе они будут удалены
                    # Но для отслеживания именно изменённых проектов кладём их в отдельный список
                    if modified_user_project[project_index]['roleId'] != role_id:
                        changed_project_ids.append(modified_user_project[project_index]['id'])
                        changed_user_names.append(username)
                    modified_user_project[project_index]['roleId'] = role_id
                    user_modified_projects[username] = modified_user_project
                except ValueError:
                    # У пользователя нет этого проекта в ролях, редактировать нечего, поэтому создаём новый экземпляр
                    project_list_to_create = new_roles.get(username, [])
                    new_project = {
                        'id': increment_and_return_id(),
                        'roleId': role_id,
                        'projectId': first(project['id'] for project in projects_raw if project['name'] == project_name),
                        'userId': first(user['userId'] for user in users if user['name'] == username),
                        'projectName': project_name # Временное поле для удобства на этапе вывода
                    }
                    project_list_to_create.append(new_project)
                    new_roles[username] = project_list_to_create

# Вывод новых проектных ролей для пользователей
print("====== Новые проектные роли для пользователей ======")
for username, projects in new_roles.items():
    print(f"## {username}")
    for project in projects:
        print(f"{project['projectName']}: {roleid_to_name(project['roleId'])}")
        del project['projectName']
    print('\n')

# Вывод изменённых проектных ролей для пользователей
print("====== Изменённые проектные роли для пользователей ======")
for username, projects in user_modified_projects.items():
    if not username in changed_user_names:
        continue
    print(f"## {username}\n")
    for project in projects:
        if project['id'] in changed_project_ids:
            print(f"{project['projectName']}: {roleid_to_name(project['roleId'])}")

print("Изменить? [y/N]")

if input().lower() not in ['y', 'yes', 'д', 'да']:
    print("Отмена операции, изменения не будут применены")
    sys.exit(0)

# Изменение проектных ролей
for username, projects in user_modified_projects.items():
    user_object = first((user for user in users if user['name'] == username), {})
    user_object['projectMemberInfos'] = user_modified_projects[username]
    req = auth.requests_session.put(URL + "api/auth/membership", json=user_object)
    if not req.ok:
        print(f"ERR: Ошибка при изменении проектов пользователя {username}. Сервер вернул код {req.status_code}")
        print(f"Ответ от сервера: {req.json()}")

# Создание новых проектных ролей
for username, project_list in new_roles.items():
    for project in project_list:
        req = auth.requests_session.post(URL + "api/auth/membership/project/" + project['projectId'], json=[project], headers={
            "Content-Type": "application/json-patch+json"
        })            
        if req.ok:
            continue

        try:
            if req.json()['errorCode'] == 'CANNOT_ASSIGN_PROJECT_ROLE_TO_ADMINISTRATOR':
                print(f"WARN: Невозможно назначить роль пользователю {username}, т.к. он администратор")
            else:
                print(f"ERR: Ошибка при назначении на проект {project['projectId']} пользователя {username}. Информация от сервера: {req.json()}")
        except KeyError:
            print(f"ERR: Ошибка при назначении на проект {project['projectId']} пользователя {username}. Информация от сервера: {req.json()}")

print("Загрузка завершена успешно!")