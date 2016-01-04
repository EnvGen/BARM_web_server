import unittest
import urllib
import app

class SampleTestCase(unittest.TestCase):
    """Test that the website shows the proper things"""
    def setUp(self):
        self.db = app.db
        self.db.create_all()
        self.client = app.app.test_client()

    def tearDown(self):
        # clear the database
        self.db.drop_all()

    def test_get_base(self):
        r = self.client.get('/')
        assert r._status_code == 200
        assert b'Hello World' in r.data
