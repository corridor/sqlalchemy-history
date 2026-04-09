import sqlalchemy as sa

from tests import TestCase


class TestRevertPolymorphicRelationship(TestCase):
    def create_models(self):
        class Car(self.Model):
            __tablename__ = "car"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            parts = sa.orm.relationship("Part", back_populates="car", cascade="all, delete-orphan", lazy="selectin")

        class Part(self.Model):
            __tablename__ = "part"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            car_id = sa.Column(sa.Integer, sa.ForeignKey(Car.id))
            car = sa.orm.relationship(Car, back_populates="parts")

            part_type = sa.Column(sa.String(50))

            __mapper_args__ = {
                "polymorphic_identity": "part",
                "polymorphic_on": part_type,
            }

        class Tire(Part):
            __tablename__ = "tire"
            __versioned__ = {}

            id = sa.Column(sa.Integer, sa.ForeignKey(Part.id), primary_key=True)
            radius = sa.Column(sa.Integer)
            width = sa.Column(sa.Integer)

            __mapper_args__ = {
                "polymorphic_identity": "tire",
            }

        self.Car = Car
        self.Part = Part
        self.Tire = Tire

    def test_revert_polymorphic_relationship(self):
        car = self.Car()
        self.session.add(car)
        self.session.commit()

        tire = self.Tire(radius=15, width=200)
        car.parts.append(tire)
        self.session.commit()

        initial_version = car.versions.all()[0]
        reverted_car = initial_version.revert(relations=["parts"])

        assert len(reverted_car.parts) == 0

        self.session.flush()
