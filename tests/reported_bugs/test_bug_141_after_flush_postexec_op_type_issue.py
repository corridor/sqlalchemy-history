import sqlalchemy as sa
from copy import copy

from tests import TestCase
from sqlalchemy_history import version_class


class TestBug141(TestCase):
    # ref: https://github.com/corridor/sqlalchemy-history/issues/141
    def create_models(self):
        class Author(self.Model):
            __tablename__ = "author"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        self.Author = Author

    def test_add_record(self):
        author = self.Author(name="Author 1")
        @sa.event.listens_for(self.session, 'after_flush_postexec')
        def after_flush_postexec(session, flush_context):
            if author.name != "yoyoyoyoyo":
                author.name = "yoyoyoyoyo"
        self.session.add(author)
        self.session.commit()

        versioned_objs = self.session.query(version_class(self.Author)).all()
        assert len(versioned_objs) == 1
        assert versioned_objs[0].operation_type == 0
        assert versioned_objs[0].name == "yoyoyoyoyo"
        author.name = "sdfeoinfe"
        self.session.add(author)
        self.session.commit()
        versioned_objs = self.session.query(version_class(self.Author)).all()
        assert len(versioned_objs) == 2
        assert versioned_objs[0].operation_type == 0
        assert versioned_objs[1].operation_type == 1
        assert versioned_objs[0].name == versioned_objs[1].name == "yoyoyoyoyo"
        sa.event.remove(self.session, "after_flush_postexec", after_flush_postexec)
