from app import db

##########
# Sample #
##########

class SampleSet(db.Model):
    __tablename__ = 'sample_set'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
  

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<SampleSet {}>'.format(self.id)


class TimePlace(db.Model):
    __tablename__ = 'time_place'

    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime())
    latitude = db.String()
    longitude = db.String()

    def __init__(self, time, latitude, longitude):
        self.time = time
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return '<TimePlace {}>'.format(self.id)


class Sample(db.Model):
    __tablename__ = 'sample'

    id = db.Column(db.Integer, primary_key=True)
    scilifelab_code = db.Column(db.String(11))
    sample_set_id = db.Column(db.Integer, db.ForeignKey('sample_set.id'))
    sample_set = db.relationship('SampleSet',
            backref=db.backref('samples'))

    timeplace_id = db.Column(db.Integer, db.ForeignKey('time_place.id'))
    timeplace = db.relationship('TimePlace',
            backref=db.backref('samples'))

    def __init__(self, scilifelab_code, sample_set):
        self.scilifelab_code = scilifelab_code
        self.sample_set = sample_set

    def __repr__(self):
        return '<Sample {}>'.format(self.id)


class SampleProperty(db.Model):
    __tablename__ = 'sample_property'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), index=True)
    value = db.Column(db.String(), index=True)
    datatype = db.Column(db.String())
    
    # Sample Property has one sample
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'))
    sample = db.relationship("Sample", 
            backref=db.backref("properties"))

    def __init__(self, name, value, datatype, sample):
        self.name = name
        self.value = value
        self.datatype = datatype
        self.sample = sample

    def __repr__(self):
        return '<SampleProperty {}>'.format(self.id)


