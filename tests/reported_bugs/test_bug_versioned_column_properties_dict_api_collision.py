from copy import copy

import sqlalchemy as sa

from sqlalchemy_history import version_class
from tests import TestCase


class TestVersionedColumnPropertiesDictAPICollision(TestCase):
    # Regression test for ``versioned_column_properties`` resolving column
    # names that shadow dict-API methods on ``mapper.attrs`` (e.g. ``values``,
    # ``keys``, ``items``). Attribute access used to return a bound method
    # instead of the column property, which made inserts on such models fail.
    def create_models(self):
        class Measurement(self.Model):
            __tablename__ = "measurement"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            values = sa.Column(sa.Integer)
            keys = sa.Column(sa.Unicode(255))
            items = sa.Column(sa.Unicode(255))

        self.Measurement = Measurement

    def test_insert_with_shadowing_column_names(self):
        measurement = self.Measurement(values=42, keys="k", items="i")
        self.session.add(measurement)
        self.session.commit()

        MeasurementVersion = version_class(self.Measurement)
        version = self.session.scalars(sa.select(MeasurementVersion)).one()
        assert version.values == 42
        assert version.keys == "k"
        assert version.items == "i"
