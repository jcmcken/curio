import unittest
from mock import Mock, patch
from curio.cli import *
import sys
import StringIO

class CLITestCase(unittest.TestCase):
    def setUp(self):
        self.cli = CurioCLI()
        self._real_stdout = sys.stdout
        self.stdout = None

    def tearDown(self):
        if self.stdout:
            sys.stdout = self._real_stdout
            self.stdout.close()
            self.stdout = None

    def capture_stdout(self):
        sys.stdout = self.stdout = StringIO.StringIO()

    def get_stdout(self):
        self.stdout.seek(0)
        result = self.stdout.read()
        self.stdout.seek(0)
        return result

    def test_invalid_path(self):
        self.assertRaises(InvalidCurioPath, self.cli._resolve_key_path, 'foo')

    def test_valid_key_path(self):
        self.assertEquals(self.cli._resolve_key_path('foo:bar'), ('foo', 'bar'))

    def test_parse_action_data(self):
        parse = self.cli._parse_action_data
        self.cli._resolve_key_path = Mock(return_value=('foo', 'bar'))
        self.assertEquals(parse([]), (None,)*4)
        self.assertEquals(parse(['get']), ('get', None, None, None))
        self.assertEquals(parse(['get', 'foo:bar']), ('get', 'foo', 'bar', None))
        self.assertEquals(parse(['get', 'foo:bar', 'baz']), ('get', 'foo', 'bar', 'baz'))

    def test_match_invalid_action(self):
        self.cli.VALID_ACTIONS = []
        self.assertRaises(RuntimeError, self.cli._match_action, 'skjdf')

    def test_match_multi_action(self):
        self.cli.VALID_ACTIONS = ['fooa', 'foob'] 
        self.assertRaises(RuntimeError, self.cli._match_action, 'foo')
        self.assertEquals(self.cli._match_action('fooa'), 'fooa')

    def test_match_auto_autocomplete(self):
        self.cli.VALID_ACTIONS = ['foo']
        self.assertEquals(self.cli._match_action('f'), 'foo')

    def test_exit_on_noop(self):
        self.cli._parser.print_help = Mock()
        fake_opts = Mock(settings=False)
        fake_args = []
        self.assertRaises(SystemExit, self.cli._exit_on_noop, fake_opts, fake_args)

    @patch('os.path.isfile')
    def test_no_config(self, mock_isfile):
        self.cli._parser.error = Mock(side_effect=SystemExit)
        mock_isfile.return_value = False
        fake_opts = Mock(config_file='blah')
        self.assertRaises(SystemExit, self.cli._exit_if_no_config, fake_opts)

    @patch('os.path.isfile')
    def test_is_config(self, mock_isfile):
        self.cli._parser.error = Mock(side_effect=SystemExit)
        mock_isfile.return_value = True
        fake_opts = Mock(config_file='blah')
        self.assertEquals(self.cli._exit_if_no_config(fake_opts), None)

    def test_route_invalid_action(self):
        self.cli._match_action = Mock(side_effect=RuntimeError('foo'))
        self.cli._parser.error = Mock(side_effect=SystemExit)
        self.assertRaises(SystemExit, self.cli._route_action, 'sjkd')

    def test_no_op_display_delete(self):
        self.capture_stdout()
        self.cli._display_result('delete', 'foo')
        self.assertEquals(self.get_stdout(), '')

    def test_no_op_display_set(self):
        self.capture_stdout()
        self.cli._display_result('set', 'foo')
        self.assertEquals(self.get_stdout(), '')

    def test_no_op_display_get(self):
        self.capture_stdout()
        self.cli._display_result('get', None)
        self.assertEquals(self.get_stdout(), '')
