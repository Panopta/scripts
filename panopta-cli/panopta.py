from panopta_rest_api import api_client
import click
import re


@click.group()
@click.argument('api-token')
@click.version_option()
@click.option('--api-version',
              default=2,
              help='The API version to use. Default: 2')
@click.pass_context
def cli(context, api_token, api_version):
    '''Manage your Panopta account.'''

    context.obj = api_client.api_client('https://api2.panopta-testing.com',
                                        api_token,
                                        version=api_version,
                                        # TODO Add logging settings to options
                                        log_level=api_client.LOG_DEBUG)


@cli.command()
@click.option('--customer-keys',
              help='Comma-separated list of customer keys')
@click.option('--dry-run', is_flag=True)
@click.option('--fqdn-pattern',
              help='Pattern for matching Fully Qualified Domain Names')
@click.option('--tags', help='Comma-separated list of tags')
@click.pass_context
def maintenance(context, customer_keys, dry_run, fqdn_pattern, tags):
    client = context.find_object(api_client.api_client)
    if dry_run:
        click.echo('DRY RUN')

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

        response = client.get('server', query_params=query_params)
        status_code = int(response['status_code'])
        if status_code == 200:
            servers.extend(response['response_data']['server_list'])
        elif status_code == 401:
            click.secho(response['status_reason'], fg='red')
            if 'partner_customer_key' in response['status_reason']:
                click.secho(query_params['partner_customer_key'], bold=True)

    if fqdn_pattern is not None:
        servers = [server for server in servers
                   if re.search(fqdn_pattern, server['fqdn']) is not None]

    server_set = set([server['name'] for server in servers])
    click.echo('\nMatching servers (' + str(len(server_set)) + '):')
    click.echo(server_set)
