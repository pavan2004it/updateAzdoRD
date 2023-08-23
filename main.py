from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import copy

payload_jobs = ('{\n  "pat": "$(pat_token)",'
                '\n  "task":"$(task_family)",'
                '\n  "service":"$(service)",'
                '\n  "container":"$(container)",'
                '\n  "image":"$(image)",'
                '\n  "project":"$(project)",'
                '\n  "sg":"$(sg)",'
                '\n  "cluster": "$(cluster)"\n}')

payload = ('{\n  "pat": "$(pat_token)",'
           '\n  "task":"$(task_family)",'
           '\n  "service":"$(service)",'
           '\n  "container":"$(container)",'
           '\n  "image":"$(image)",'
           '\n  "containerPort":"$(containerport)",'
           '\n  "cluster": "$(cluster)",'
           '\n  "sg":"$(sg)",'
           '\n  "targetgroupname": "$(service)-tg"\n}')


def auth():
    # Replace with your Azure DevOps URL and project name
    organization_url = "https://dev.azure.com/RinggitPay"
    # Replace with your PAT
    personal_access_token = "qf3i3xxb24nbkmxaubs7jhm5fpl6pjknf3br7th563ipnzxqdqba"
    # Create a connection to your organization
    credentials = BasicAuthentication("", personal_access_token)
    return [organization_url, credentials]


def modify_env_name():
    connection_strings = auth()
    connection = Connection(base_url=connection_strings[0], creds=connection_strings[1])
    release_client = connection.clients_v7_1.get_release_client()
    project_names = ["RinggitPay.Identity", "RinggitPay.PaymentGateway", "RinggitPay.CustomForms",
                     "RinggitPay.Products"]
    for project_name in project_names:
        # Get all release definitions
        release_definitions = release_client.get_release_definitions(
            project=project_name, query_order="NameAscending"
        )

        # Modify the name of all release definitions and update them
        for rd in release_definitions:
            release_definition = release_client.get_release_definition(
                project=project_name, definition_id=rd.id
            )
            print(f"Modifying release definition {rd.id}: {rd.name}")
            for env in release_definition.environments:
                if env.name == "Dev":
                    env.name = "dev"
            release_client.update_release_definition(
                release_definition=release_definition, project=project_name
            )


def modify_task(project_name: str, base_url: str, creds: str, payload_data: str, release_id: str):
    connection = Connection(base_url=base_url, creds=creds)
    release_client = connection.clients_v7_1.get_release_client()
    new_name = ""
    release_definition = release_client.get_release_definition(project=project_name, definition_id=release_id)
    release_def = release_client.get_release_definition(definition_id=release_id,project=project_name)
    for k, v in release_def.variables.items():
        if k == "service":
            new_name = v.value
    for env in release_definition.environments:
        env.variables["cluster"] = {
            "value": "rp-" + env.name.lower() + "-cluster",  # Replace with the variable value you want to set
            "allowOverride": True
        }
        env.variables["sg"] = {
            "value": "RP-" + env.name.upper() + "-ECS-PRV-SG",  # Replace with the variable value you want to set
            "allowOverride": True
        }
        env.variables["service"] = {
            "value": new_name.replace("rp-","rp-"+env.name.lower()+"-"),
            "allowOverride": True
        }
        env.variables["task_family"] = {
            "value": new_name.replace("rp-","rp-"+env.name.lower()+"-"),
            "allowOverride": True
        }
        env.variables["container"] = {
            "value": new_name.replace("rp-","rp-"+env.name.lower()+"-"),
            "allowOverride": True
        }

        for phase in env.deploy_phases:
            for task in phase['workflowTasks']:
                if task['taskId'] == 'c9e49f96-6c7d-4420-97f1-5e0dfd816354':
                    task['inputs']['payload'] = payload_data

    release_client.update_release_definition(
        release_definition=release_definition, project=project_name)


def modify_release_definition():
    connection_strings = auth()
    connection = Connection(base_url=connection_strings[0], creds=connection_strings[1])
    release_client = connection.clients_v7_1.get_release_client()
    project_names = ["RinggitPay.Identity", "RinggitPay.PaymentGateway", "RinggitPay.CustomForms",
                     "RinggitPay.Products"]
    for project_name in project_names:
        # Get all release definitions
        release_definitions = release_client.get_release_definitions(
            project=project_name, query_order="NameAscending"
        )

        # Modify the name of all release definitions and update them
        for rd in release_definitions:
            print(f"Modifying release definition {rd.id}: {rd.name}")
            if "Jobs" in rd.name:
                modify_task(project_name, connection_strings[0], connection_strings[1], payload_jobs, rd.id)
            else:
                modify_task(project_name, connection_strings[0], connection_strings[1], payload, rd.id)


def create_environment(env_name: str):
    connection_strings = auth()
    connection = Connection(base_url=connection_strings[0], creds=connection_strings[1])
    release_client = connection.clients_v7_1.get_release_client()
    project_names = ["RinggitPay.Identity", "RinggitPay.PaymentGateway", "RinggitPay.CustomForms",
                     "RinggitPay.Products"]
    for project_name in project_names:
        # Get the release definition you want to modify
        release_definitions = release_client.get_release_definitions(
            project=project_name, query_order="NameAscending"
        )
        for rd in release_definitions:
            release_definition = release_client.get_release_definition(
                project=project_name, definition_id=rd.id
            )

            # Find the "Dev" environment and clone it
            dev_env = None
            for env in release_definition.environments:
                if env.name == "Dev":
                    dev_env = env
                    break

            if dev_env is not None:
                # Check if the "UAT" environment already exists
                uat_exists = False
                for env in release_definition.environments:
                    if env.name == env_name:
                        uat_exists = True
                        break

                if not uat_exists:
                    # Clone the "Dev" environment and create the "UAT" environment
                    uat_env = copy.deepcopy(dev_env)
                    uat_env.name = env_name
                    uat_env.id = 0
                    uat_env.rank = max(env.rank for env in release_definition.environments) + 1

                    # Add the "UAT" environment to the release definition
                    release_definition.environments.append(uat_env)

                    # Update the release definition with the new environment
                    release_client.update_release_definition(
                        release_definition=release_definition, project=project_name
                    )
                    print("Created Uat environment.")
                else:
                    print("Uat environment already exists.")
            else:
                print("Dev environment not found.")


def delete_release_variables():
    vars_to_delete = ["service", "task_family", "container"]
    connection_strings = auth()
    connection = Connection(base_url=connection_strings[0], creds=connection_strings[1])
    release_client = connection.clients_v7_1.get_release_client()
    project_names = ["RinggitPay.Identity", "RinggitPay.PaymentGateway", "RinggitPay.CustomForms",
                     "RinggitPay.Products"]
    for project_name in project_names:
        # Get the release definition you want to modify
        release_definitions = release_client.get_release_definitions(
            project=project_name, query_order="NameAscending"
        )
        for rd in release_definitions:
            release_definition = release_client.get_release_definition(
                project=project_name, definition_id=rd.id
            )
            for var in vars_to_delete:
                if var in release_definition.variables.keys():
                    del release_definition.variables[var]
            print(f"Modifying release definition {rd.id}: {rd.name}")
            release_client.update_release_definition(release_definition, project=project_name)


# create_environment("uat")
# modify_release_definition()
# delete_release_variables()
# modify_env_name()


