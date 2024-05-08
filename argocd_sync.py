from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
import os
import time  # for the sleep function

# From arguments
RUNTIME = os.getenv('RUNTIME')
APPLICATION = os.getenv('APPLICATION')
SYNC_OPT_PRUNE = (os.getenv('SYNC_OPT_PRUNE', 'false').lower() == 'true')
SYNC_OPT_FORCE = (os.getenv('SYNC_OPT_FORCE', 'false').lower() == 'true')
SYNC_OPT_PRUNE_LAST = (os.getenv('SYNC_OPT_PRUNE_LAST', 'false').lower())
SYNC_OPT_APPLY_OUT_OF_SYNC_ONLY = (os.getenv('SYNC_OPT_APPLY_OUT_OF_SYNC_ONLY', 'false').lower())
SYNC_OPT_SERVER_SIDE_APPLY = (os.getenv('SYNC_OPT_SERVER_SIDE_APPLY', 'true').lower())


# From execution context
CF_URL = os.getenv('CF_URL', 'https://g.codefresh.io')
CF_API_KEY = os.getenv('CF_API_KEY')
CF_STEP_NAME = os.getenv('CF_STEP_NAME', 'STEP_NAME')


###############################################################################


def main():
    ingress_host = get_runtime_ingress_host()
    terminate_current_app_operation(ingress_host)
    execute_argocd_sync(ingress_host)
    # Generating link to the Apps Dashboard
    CF_OUTPUT_URL_VAR = CF_STEP_NAME + '_CF_OUTPUT_URL'
    link_to_app = get_link_to_apps_dashboard()
    export_variable(CF_OUTPUT_URL_VAR, link_to_app)


###############################################################################

def get_query(query_name):
    # To do: get query content from a variable, failback to a file
    with open('queries/'+query_name+'.graphql', 'r') as file:
        query_content = file.read()
    return gql(query_content)


def get_runtime():
    transport = RequestsHTTPTransport(
        url=CF_URL + '/2.0/api/graphql',
        headers={'authorization': CF_API_KEY},
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)
    query = get_query('getRuntime')  # gets gql query
    variables = {
        "runtime": RUNTIME
    }
    runtime = client.execute(query, variable_values=variables)
    return runtime


def get_runtime_ingress_host():
    ingress_host = None
    runtime = get_runtime()
    ingress_host = runtime['runtime']['ingressHost']
    return ingress_host


def get_link_to_apps_dashboard():
    runtime = get_runtime()
    runtime_ns = runtime['runtime']['metadata']['namespace']
    url_to_app = CF_URL+'/2.0/applications-dashboard/' + \
        runtime_ns+'/'+RUNTIME+'/'+APPLICATION+'/timeline'
    return url_to_app


def terminate_query(ingress_host):
    '''
    Executes the GraphQL query to terminate the current operation based on the 
    app in the Global Variables and the provided Ingress Host
    '''
    runtime_api_endpoint = ingress_host + '/app-proxy/api/graphql'
    transport = RequestsHTTPTransport(
        url=runtime_api_endpoint,
        headers={'authorization': CF_API_KEY},
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)
    query = get_query('terminate')  # gets gql query
    variables = {
        "appName": APPLICATION
    }
    print("Terminating current operation in app: ", variables)
    result = client.execute(query, variable_values=variables)
    print(result)


def terminate_current_app_operation(ingress_host):
    needsToTerminate=True
    try:
        terminate_query(ingress_host)
        print('Terminating current operation in app, ',
              'so the current sync action could be performed. Waiting 30 seconds.')
    except Exception as e:
        # if the error message is because there's NO operatation to termiante
        if str(e).find("Reason: Bad Request") > 0:
            print(f'Error: {e}')
            raise Exception(
                f'Error trying to terminate the current operation of the app')
        else:
            needsToTerminate=False
            print("The app doesn't have any current operation. ",
                  "No need to terminate operations. Continuing...")
    if needsToTerminate is True:
        print("Waiting for the current operation in the app to be successfully terminated.")
        time.sleep(30)


def execute_argocd_sync(ingress_host):
    runtime_api_endpoint = ingress_host + '/app-proxy/api/graphql'
    transport = RequestsHTTPTransport(
        url=runtime_api_endpoint,
        headers={'authorization': CF_API_KEY},
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)
    query = get_query('argocd_sync')  # gets gql query
    variables = {
        "applicationName": APPLICATION,
        "options": {
            "name": APPLICATION,
            "dryRun": False,
            "prune": SYNC_OPT_PRUNE,
            "strategy": {
                "hook": {
                    "force": SYNC_OPT_FORCE
                }
            },
            "syncOptions": {
                "items": [
                    "PruneLast="+SYNC_OPT_PRUNE_LAST,
                    "ApplyOutOfSyncOnly="+SYNC_OPT_APPLY_OUT_OF_SYNC_ONLY,
                    "ServerSideApply="+SYNC_OPT_SERVER_SIDE_APPLY,
                    "PrunePropagationPolicy=foreground"
                ]
            },
            "resources": None
        }
    }
    print("Syncing app: ", variables)
    result = client.execute(query, variable_values=variables)
    print(result)


def export_variable(var_name, var_value):
    # if this script is executed in CF build
    if os.getenv('CF_BUILD_ID') != None:
        # exporting var when used as a freestyle step
        path = str(os.getenv('CF_VOLUME_PATH'))
        with open(path+'/env_vars_to_export', 'a') as a_writer:
            a_writer.write(var_name + "=" + var_value+'\n')
        # exporting var when used as a plugin
        with open('/meta/env_vars_to_export', 'a') as a_writer:
            a_writer.write(var_name + "=" + var_value+'\n')

    print("Exporting variable: "+var_name+"="+var_value)

###############################################################################


if __name__ == "__main__":
    main()
