import os.path
import unittest

from weathercheck import rainNowcast

class TestRainNowcast(unittest.TestCase):
    def set_up(self):
        self.assertTrue(os.path.isfile(rainNowcast.driver_path))


if __name__ == '__main__':
    unittest.main()