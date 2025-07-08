import unittest
import sys
import os
import subprocess
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.security import sanitize_input, validate_sql, sandbox_python_execution

class TestSecurity(unittest.TestCase):

    def test_sanitize_input(self):
        self.assertEqual(sanitize_input("hello;world"), "helloworld")
        self.assertEqual(sanitize_input("test&ing"), "testing")
        self.assertEqual(sanitize_input("foo|bar"), "foobar")
        self.assertEqual(sanitize_input("a<b"), "ab")
        self.assertEqual(sanitize_input("c>d"), "cd")
        self.assertEqual(sanitize_input("normal string"), "normal string")
        self.assertEqual(sanitize_input(123), "123") # Test non-string input

    def test_validate_sql(self):
        # Valid SQL
        self.assertTrue(validate_sql("SELECT * FROM users")[0])
        self.assertTrue(validate_sql("INSERT INTO products (name) VALUES ('test')")[0])
        self.assertTrue(validate_sql("UPDATE orders SET status='shipped' WHERE id=1")[0])
        self.assertTrue(validate_sql("CREATE TABLE new_table (id INT)")[0])

        # Invalid SQL (injection attempts)
        self.assertFalse(validate_sql("SELECT * FROM users; --")[0])
        self.assertFalse(validate_sql("SELECT * FROM users; /* comment */")[0])
        self.assertFalse(validate_sql("DROP TABLE users")[0])
        self.assertFalse(validate_sql("DELETE FROM products")[0])
        self.assertFalse(validate_sql("UNION SELECT null, null")[0])
        self.assertFalse(validate_sql("SELECT * FROM users INTO OUTFILE '/tmp/test.txt'")[0])
        self.assertFalse(validate_sql("EXEC xp_cmdshell('dir')")[0])
        self.assertFalse(validate_sql("SELECT * FROM users WHERE id = 1 OR 1=1")[0]) # Simple OR injection

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_sandbox_python_execution_success(self, mock_tempfile, mock_subprocess_run):
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "/tmp/test_code.py"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file_obj

        mock_subprocess_run.return_value = MagicMock(
            returncode=0,
            stdout="Hello from sandbox\n",
            stderr=""
        )

        code = "print('Hello from sandbox')"
        result = sandbox_python_execution(code)
        self.assertEqual(result, "Hello from sandbox\n")
        mock_temp_file_obj.write.assert_called_once_with(code.encode())
        mock_subprocess_run.assert_called_once()

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_sandbox_python_execution_timeout(self, mock_tempfile, mock_subprocess_run):
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "/tmp/test_code.py"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file_obj

        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=5)

        code = "import time; time.sleep(10)"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code execution timed out", result)

    def test_sandbox_python_execution_forbidden_import(self):
        code = "import os"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Importing module 'os' is not allowed", result)

        code = "from subprocess import run"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Importing module 'subprocess' is not allowed", result)

    def test_sandbox_python_execution_dangerous_pattern(self):
        code = "eval('1+1')"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: eval\\(", result)

        # This test case will now correctly assert on __class__ because it's matched first
        code = "().__class__.__bases__"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: \\b__class__\\b", result)

        code = "().__class__.__subclasses__"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: \\b__class__\\b", result)

        code = "().__class__.__mro__"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: \\b__class__\\b", result)

        code = "().__class__.mro()"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: \\b__class__\\b", result)

        code = "globals()"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: globals\\(", result)

        code = "locals()"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: locals\\(", result)

        code = "getattr(obj, 'attr')"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: getattr\\(", result)

        code = "setattr(obj, 'attr', val)"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: setattr\\(", result)

        code = "delattr(obj, 'attr')"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: delattr\\(", result)

        code = "exec('print(1)')"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: exec\\(", result)

        code = "compile('1+1', '', 'eval')"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: compile\\(", result)

        code = "open('file.txt', 'w')"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: open\\(", result)

        code = "file('file.txt', 'w')"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: file\\(", result)

        code = "__import__('os')"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: __import__\\(", result)

        code = "().__builtins__"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: \\b__builtins__\\b", result)

        code = "().__globals__"
        result = sandbox_python_execution(code)
        self.assertIn("Error: Code contains potentially dangerous pattern: \\b__globals__\\b", result)


if __name__ == '__main__':
    unittest.main()