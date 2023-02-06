import sqlalchemy as sa
from tests import TestCase


class TestBug25(TestCase):
    # ref: https://github.com/corridor/sqlalchemy-history/issues/25
    def create_models(self):
        class Writer(self.Model):
            __tablename__ = "writer"
            __versioned__ = {}

            id = sa.Column(sa.Integer, sa.Sequence(f"{__tablename__}_seq"), primary_key=True)
            name = sa.Column(sa.String(255))
            type = sa.Column(sa.String(255))

            __mapper_args__ = {
                "polymorphic_on": (
                    sa.case(
                        [(type.in_(["poet", "lyricist"]), "bard")],
                        else_=type,
                    )
                ),
                "polymorphic_identity": "writer",
            }

        class Author(self.Model):
            __tablename__ = "author"
            __versioned__ = {}
            id = sa.Column(sa.Integer, sa.Sequence(f"{__tablename__}_seq"), primary_key=True)
            name = sa.Column(sa.String(255))

            __mapper_args__ = {
                "polymorphic_identity": "author",
            }

        self.Writer = Writer
        self.Author = Author

    def test_inserting_entries(self):
        writer = self.Writer(name="Writer 1")
        author = self.Author(name="Author 1")
        self.session.add(writer)
        self.session.add(author)
        self.session.commit()
