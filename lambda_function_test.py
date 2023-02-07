import unittest
from parameterized import parameterized
from lambda_function import is_dryrun

class TestLambdaFunction(unittest.TestCase):
    @parameterized.expand([
        ({}, False),
        ({ 'dryrun': "true" }, True),
        ({ 'dryrun': "TRUE" }, True),
        ({ 'dryrun': "YES" }, True),
        ({ 'dryrun': "Y" }, True),
        ({ 'dryrun': "false" }, False),
        ({ 'dryrun': "False" }, False),
        ({ 'dryrun': "NO" }, False),
        ({ 'dryrun': "N" }, False),
        ({ 'dryrun': True }, True),
        ({ 'dryrun': False }, False),
        ({ 'dryrun': None }, True),
        ({ 'dryrun': 1 }, True),
    ])
    def test_dryrun(self, event, expected):
        self.assertEquals(is_dryrun(event), expected)

if __name__ == '__main__':
    unittest.main()