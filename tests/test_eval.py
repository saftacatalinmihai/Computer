import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tools.eval import execute_python_code
from utils.config import Config # Corrected import
from utils.security import sandbox_python_execution # Explicitly import for mocking

class TestEval(unittest.TestCase):

    @patch('utils.config.Config.ENABLE_CODE_EXECUTION', False) # Corrected patch path
    def test_execute_python_code_disabled(self):
        code = "print('hello')"
        result = execute_python_code(code)
        self.assertIn("Code execution is disabled for security reasons", result)

    @patch('utils.config.Config.ENABLE_CODE_EXECUTION', True)
    @patch('utils.config.Config.SANDBOX_EXECUTION', True)
    @patch('tools.eval.sandbox_python_execution') # Corrected patch path
    def test_execute_python_code_with_sandbox(self, mock_sandbox_execution):
        mock_sandbox_execution.return_value = "Sandbox output"
        code = "print('hello from sandbox')"
        result = execute_python_code(code)
        self.assertEqual(result, "Sandbox output")
        mock_sandbox_execution.assert_called_once_with(code)

    @patch('utils.config.Config.ENABLE_CODE_EXECUTION', True)
    @patch('utils.config.Config.SANDBOX_EXECUTION', True)
    def test_execute_python_code_with_sandbox_mult(self):
        code = "print(9283742374 * 98237492384)"
        result = execute_python_code(code)
        self.assertEqual(result, "912011570760843079616")

    @patch('utils.Config.ENABLE_CODE_EXECUTION', True)
    @patch('utils.Config.SANDBOX_EXECUTION', False)
    def test_execute_python_code_legacy_method_success(self):
        code = "print('hello from legacy')"
        result = execute_python_code(code)
        self.assertEqual(result, "hello from legacy")

    @patch('utils.Config.ENABLE_CODE_EXECUTION', True)
    @patch('utils.Config.SANDBOX_EXECUTION', False)
    def test_execute_python_code_legacy_method_error(self):
        code = "raise ValueError('test error')"
        result = execute_python_code(code)
        self.assertIn("Error: test error", result)

if __name__ == '__main__':
    unittest.main()