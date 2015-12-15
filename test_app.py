import unittest
import app
from models import Sample

class SampleTestCase(unittest.TestCase):
    """Test that a sample in the database has the correct relations"""
    def setUp(self):
        
        self.db = app.db
       
        self.session = self.db.session

        self.connection = self.session.connection()

        self.trans = self.connection.begin()

    def tearDown(self):
        # clear the database
        self.session.close()

        self.trans.rollback()

        self.connection.close()

    def test_app(self):
        all_samples_before = Sample.query.all()
        assert len(all_samples_before) == 0
        sample = Sample("P1993_101", None)
        self.session.add(sample)
        self.session.commit()

        all_samples_after = Sample.query.all()
        assert len(all_samples_after) == 1