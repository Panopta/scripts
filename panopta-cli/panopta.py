from datetime import datetime
from delorean import Delorean, parse
import api_client
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
@click.option('--start', help='Start time for the maintenance period. Default: now')
@click.option('--end', help='End time for the maintenance period. Default: one minute from start')
@click.pass_context
def maintenance(context, customer_keys, dry_run, fqdn_pattern, tags, start, end):
    client = context.find_object(api_client.api_client)
    if dry_run:
        click.secho('\nDRY RUN\n', bold=True)

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
        else:
            raise click.ClickException('Response from API: "{}"'.format(response['status_reason']))

    if fqdn_pattern is not None:
        servers = [server for server in servers
                   if re.search(fqdn_pattern, server['fqdn']) is not None]

    start_time = parse(start) if start else Delorean()
    end_time = parse(end) if end else start_time.next_minute()
    duration = int(round((end_time - start_time).total_seconds() / 60))
    if duration < 0:
        raise click.BadOptionUsage(
            start,
            'Start time ({}) must occur before end time ({})'.format(start_time.datetime, end_time.datetime)
        )
    elif duration < 1:
        raise click.BadOptionUsage(
            end,
            'End time ({}) must be at least one minute after start time ({})'.format(
                end_time.datetime, start_time.datetime)
        )

    click.echo('Creating scheduled maintenance from {} to {} ({} minute{}) for {} servers:'.format(
        start_time.datetime.strftime('%c'),
        end_time.datetime.strftime('%c'),
        duration,
        's' if duration > 1 else '',
        str(len(servers)))
    )
    # `server['url'].split('/')[-1]` gets the server's id
    server_names = ['{} ({})'.format(server['name'], server['url'].split('/')[-1]) for server in servers]
    server_names.sort()
    for name in server_names:
        click.echo(' * {}'.format(name))

    if dry_run:
        return

    request_data = {
        'description': 'Created using Panopta CLI',
        'duration': duration,
        'name': 'Scheduled Maintenance',
        'original_start_time': start_time.datetime.isoformat(),
        'targets': [server['url'] for server in servers],
    }
    response = client.post('maintenance_schedule', request_data)
    if int(response['status_code']) == 201:
        maintenance_schedule_id = response['response_headers']['id']
        click.echo('Successfully created maintenance schedule {}'.format(maintenance_schedule_id))
    else:
        raise click.ClickException('Response from API: "{}"'.format(response['status_reason']))
