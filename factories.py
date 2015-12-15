import factory
from app import db
from factory.alchemy import SQLAlchemyModelFactory

class SampleFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Sample
        sqlalchemy_session = db.session

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(
