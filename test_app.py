import unittest
import app
from models import Sample, SampleSet, TimePlace
import datetime

class SampleTestCase(unittest.TestCase):
    """Test that a sample in the database has the correct relations"""
    def setUp(self):
        
        self.db = app.db

        self.db.create_all()

        self.session = self.db.session

        self.connection = self.session.connection()

        self.trans = self.connection.begin()

    def tearDown(self):
        # clear the database
        self.session.close()

        self.trans.rollback()

        self.connection.close()
        
        self.db.drop_all()

    def test_sample(self):
        all_samples_before = Sample.query.all()
        assert len(all_samples_before) == 0
        sample = Sample("P1993_101", None, None)
        self.session.add(sample)
        self.session.commit()

        all_samples_after = Sample.query.all()
        assert len(all_samples_after) == 1

    def test_sample_sampleset(self):
        #Test that sample and sample set references each other properly
        sample_set = SampleSet("first_sampleset")
        sample1 = Sample("P1993_101", sample_set, None)

        self.session.add(sample1)
        self.session.add(sample_set)

        # Sample sets relations are created
        assert Sample.query.filter_by(scilifelab_code='P1993_101').first().sample_set is sample_set

        sample_set2 = SampleSet("second_sampleset")
        sample2 = Sample("P1993_102", sample_set2, None)
        sample3 = Sample("P1993_103", sample_set, None)
        self.session.add(sample2)
        self.session.add(sample3)

        self.session.commit()

        # Sample2 should have sample set 2
        assert Sample.query.filter_by(scilifelab_code='P1993_102').first().sample_set is sample_set2

        # There should be 2 sample sets and 3 samples in the db
        assert len(SampleSet.query.all()) == 2
        assert len(Sample.query.all()) == 3

        # The reverse relationship for sample set 2 should have sample1 and sample3
        assert len(sample_set.samples) == 2

        assert sample2 not in sample_set.samples
        assert sample1 in sample_set.samples
        assert sample3 in sample_set.samples

    def test_sample_timeplace(self):
        sample_set = SampleSet("first_sampleset")
        sample1 = Sample("P1993_101", sample_set, None)
        time_place1 = TimePlace(datetime.datetime.now(), "52.3820818", "18.0233369")
        sample1.timeplace = time_place1
        self.session.add(sample1)
        self.session.add(time_place1)
        # The sample should have the correct time place
        assert Sample.query.first().timeplace == time_place1

        # One can also add it after sample creation
        sample2 = Sample("P1993_102", sample_set, None)
        sample2.timeplace = time_place1

        self.session.add(sample2)
        self.session.commit()

        # The only existing time place should contain exactly sample1 and sample2
        assert len(TimePlace.query.first().samples) == 2
        assert sample1 in TimePlace.query.first().samples
        assert sample2 in TimePlace.query.first().samples
