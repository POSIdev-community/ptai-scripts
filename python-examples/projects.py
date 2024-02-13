import auth
from consts import BASE_URL


def get_all_projects() -> list[dict[str, any]]:
    res = auth.requests_session.get(BASE_URL + "api/projects")
    json = res.json()

    return json


def get_projects_in_queue() -> list[str]:
    res = auth.requests_session.get(BASE_URL + "api/scans")
    json = res.json()

    ids = list(map(lambda element: element["projectId"], json))

    return ids


def get_scanning_projects() -> list[str]:
    res = auth.requests_session.get(BASE_URL + "api/scanAgents")
    json = res.json()

    currently_scanning_agents = list(filter(lambda agent: agent["statusType"] == "Scan", json))
    ids = list(map(lambda agent: agent["projectId"], currently_scanning_agents))

    return ids


def main():
    # disable SSL check
    auth.requests_session.verify = False

    auth.do_auth()

    # let's get projects via API
    projects = get_all_projects()
    for project in projects:
        print("id = %s" % project["id"])
        print("name = %s" % project["name"])
        print("creationDate = %s" % project["creationDate"])
        print("settingsId = %s" % project["settingsId"])

    projects_in_scan_queue = get_projects_in_queue()
    for project_id in projects_in_scan_queue:
        print("project with ID=%s in queue" % project_id)

    scanning_projects = get_scanning_projects()
    for project_id in scanning_projects:
        print("project with ID=%s is scanning" % project_id)


if __name__ == "__main__":
    main()
