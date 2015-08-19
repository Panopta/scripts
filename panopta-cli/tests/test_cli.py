from click.testing import CliRunner
from panopta_rest_api import api_client
import panopta
import sure
import unittest


class MockClient(api_client.api_client):
    INVALID_API_TOKEN = 'invalid-api-token'
    INVALID_CUSTOMER_KEY = 'invalid-customer-key'

    def __init__(self):
        self.api_token = 'valid-api-token'
        self.get_requests = []

    def get(self, __, **kwargs):
        if self.api_token == self.INVALID_API_TOKEN:
            return {'status_code': 401,
                    'status_reason': 'error: Authentication failed'}

        query_params = kwargs['query_params']
        self.get_requests.append({'query_params': query_params})

        customer_key = query_params.get('partner_customer_key', None)
        if customer_key == self.INVALID_CUSTOMER_KEY:
            return {'status_code': 401,
                    'status_reason': 'error: Invalid partner_customer_key'}

        return {'status_code': 200,
                'status_reason': 'OK',
                'response_headers': {'status': 200},
                'response_data': {'server_list': [
                    {'name': 'one', 'fqdn': 'abc'},
                    {'name': 'two', 'fqdn': 'xyz'}
                ]}}


class TestMaintenanceCommand(unittest.TestCase):
    def setUp(self):
        self.mock_client = MockClient()
        self.runner = CliRunner()

    def test_invalid_api_token_is_noted_in_output(self):
        self.mock_client.api_token = MockClient.INVALID_API_TOKEN
        result = self.runner.invoke(panopta.maintenance, obj=self.mock_client)

        result.exit_code.should.equal(0)
        result.output.should.contain('error: Authentication failed')
        result.output.should.contain('Matching servers (0)')

    def test_with_no_options(self):
        result = self.runner.invoke(panopta.maintenance, obj=self.mock_client)

        result.exit_code.should.equal(0)
        result.exception.should.be(None)

    def test_multiple_customer_keys_makes_multiple_get_requests(self):
        fake_keys = range(5)
        fake_keys_csv = ','.join(map(str, fake_keys))
        result = self.runner.invoke(panopta.maintenance,
                                    ['--customer-keys', fake_keys_csv],
                                    obj=self.mock_client)

        result.exit_code.should.equal(0)
        len(self.mock_client.get_requests).should.equal(len(fake_keys))

    def test_invalid_customer_keys_are_noted_in_output(self):
        result = self.runner.invoke(panopta.maintenance,
                                    ['--customer-keys',
                                     MockClient.INVALID_CUSTOMER_KEY],
                                    obj=self.mock_client)

        result.exit_code.should.equal(0)
        result.output.should.contain('error: Invalid partner_customer_key')
        result.output.should.contain(MockClient.INVALID_CUSTOMER_KEY)

    def test_tags_are_added_to_every_request(self):
        result = self.runner.invoke(panopta.maintenance,
                                    ['--customer-keys',
                                     '1,2,3',
                                     '--tags',
                                     'TestTag'],
                                    obj=self.mock_client)

        result.exit_code.should.equal(0)
        for request in self.mock_client.get_requests:
            request['query_params']['tags'].should.contain('TestTag')

    def test_fqdn_pattern_filters_server_list(self):
        result = self.runner.invoke(panopta.maintenance,
                                    ['--customer-keys',
                                     '1,2,3',
                                     '--fqdn-pattern',
                                     'abc'],
                                    obj=self.mock_client)

        result.exit_code.should.equal(0)
        result.output.should.contain('one')
        result.output.shouldnt.contain('two')

    def test_dry_run_makes_no_post_requests(self):
        result = self.runner.invoke(panopta.maintenance,
                                    ['--dry-run'],
                                    obj=self.mock_client)

        result.exit_code.should.equal(0)
        result.output.should.contain('DRY RUN')
        result.output.shouldnt.contain('Servers affected')
