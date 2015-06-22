from click.testing import CliRunner
from panopta_rest_api import api_client
import panopta
import sure
import unittest


class MockClient(api_client.api_client):
    def __init__(self):
        self.get_requests = []

    def get(self, __, **kwargs):
        self.get_requests.append({'query_params': kwargs['query_params']})
        return {'status_code': 200,
                'status_reason': 'OK',
                'response_headers': {"status": 200},
                'response_data': {'server_list': [
                    {'name': 'one', 'fqdn': 'abc'},
                    {'name': 'two', 'fqdn': 'xyz'}
                ]}}


class TestPanoptaCommand(unittest.TestCase):
    @unittest.skip('TODO')
    def test_invalid_api_token_is_noted_in_output(self):
        pass


class TestMaintenanceCommand(unittest.TestCase):
    def setUp(self):
        self.mock_client = MockClient()
        self.runner = CliRunner()

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

    @unittest.skip('WIP')
    def test_invalid_customer_keys_are_noted_in_output(self):
        result = self.runner.invoke(panopta.maintenance,
                                    ['--customer-keys',
                                     '1,2,wrong'],
                                    obj=self.mock_client)

        result.exit_code.should.equal(0)
        result.output.should.contain('Invalid customer key')

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
