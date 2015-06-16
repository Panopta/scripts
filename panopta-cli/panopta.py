from panopta_rest_api import api_client
import click
import re


@click.group()
@click.argument('token')
@click.option('--api-version',
              default=2,
              help='The API version to use, default: "2"')
@click.pass_context
def cli(context, token, api_version):
    context.obj = {}
    context.obj['client'] = api_client.api_client(
        'https://api2.panopta-testing.com',
        token,
        version=api_version,
        # TODO Add logging settings to options
        log_level=api_client.LOG_DEBUG
    )


@cli.command()
@click.option('--customer-keys',
              help='Comma-separated list of customer keys')
@click.option('--fqdn-pattern',
              help='Pattern for matching Fully Qualified Domain Names')
@click.option('--tags', help='Comma-separated list of tags')
@click.pass_context
def maintenance(context, customer_keys, fqdn_pattern, tags):
    requests = []
    if customer_keys is not None:
        for key in customer_keys.split(','):
            requests.append({'partner_customer_key': key})
    else:
        requests.append({})

    servers = []
    for query_params in requests:
        if tags is not None:
            query_params.update({'tags': tags})

        response = context.obj['client'].get('server',
                                             query_params=query_params)
        if int(response['status_code']) is 200:
            servers.extend(response['response_data']['server_list'])
        else:
            pass  # TODO Should we notify them that some of the requests failed?

    if fqdn_pattern is not None:
        servers = [server for server in servers
                   if re.search(fqdn_pattern, server['fqdn']) is not None]

    print([server['name'] for server in servers])
