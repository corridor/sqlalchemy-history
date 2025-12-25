from __future__ import annotations

from copy import copy

import sqlalchemy as sa

from tests import TestCase


class TestBug97(TestCase):
    # ref: https://github.com/corridor/sqlalchemy-history/issues/97
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            name = sa.Column(sa.Unicode(255), server_default="default name")
            content = sa.Column(sa.UnicodeText)

        self.Article = Article

    def test_should_not_pick_default_entry_in_versions(self):
        article = self.Article(name="Article 1")
        self.session.add(article)
        self.session.commit()
        article.name = None
        self.session.add(article)
        self.session.commit()
        assert article.name is None
        assert article.versions.count() == 2
        assert article.versions.all()[-1].name is None
