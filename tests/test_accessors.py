from copy import copy

import sqlalchemy as sa

from sqlalchemy_history.utils import tx_column_name
from tests import TestCase, create_test_cases


class VersionModelAccessorsTestCase(TestCase):
    def test_previous_for_first_version(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        assert not article.versions[0].previous

    def test_previous_for_live_parent(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        article.name = "Updated name"
        article.content = "Updated content"
        session.commit()
        version = article.versions[1]

        assert version.previous.name == "Some article"
        assert getattr(version.previous, tx_column_name(version)) == getattr(version, tx_column_name(version)) - 1

    def test_previous_for_deleted_parent(self, session, versioning_options):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        session.delete(article)
        session.commit()
        versions = session.scalars(
            sa.select(self.ArticleVersion).order_by(
                getattr(self.ArticleVersion, versioning_options["transaction_column_name"])
            )
        ).all()
        assert versions[1].previous.name == "Some article"

    def test_previous_chaining(self, session, versioning_options):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        article.name = "Updated article"
        session.commit()
        session.delete(article)
        session.commit()
        version = session.scalars(
            sa.select(self.ArticleVersion).order_by(
                getattr(self.ArticleVersion, versioning_options["transaction_column_name"])
            )
        ).all()[-1]
        assert version.previous.previous

    def test_previous_two_versions(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        article2 = self.Article()
        article2.name = "Second article"
        article2.content = "Second article"
        session.add(article2)
        session.commit()

        article.name = "Updated article"
        session.commit()
        article.name = "Updated article 2"
        session.commit()

        assert article.versions[2].previous
        assert article.versions[1].previous
        assert article.versions[2].previous == article.versions[1]
        assert article.versions[1].previous == article.versions[0]

    def test_next_two_versions(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        article2 = self.Article()
        article2.name = "Second article"
        article2.content = "Second article"
        session.add(article2)
        session.commit()

        article.name = "Updated article"
        session.commit()
        article.name = "Updated article 2"
        session.commit()

        assert article.versions[0].next
        assert article.versions[1].next
        assert article.versions[0].next == article.versions[1]
        assert article.versions[1].next == article.versions[2]

    def test_next_for_last_version(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        assert not article.versions[0].next

    def test_next_for_live_parent(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        article.name = "Updated name"
        article.content = "Updated content"
        session.commit()
        version = article.versions[0]

        assert version.next.name == "Updated name"

    def test_next_for_deleted_parent(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        version = article.versions[0]
        session.delete(article)
        session.commit()

        assert version.next

    def test_chaining_next(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        article.name = "Updated article"
        session.commit()
        article.content = "Updated content"
        session.commit()

        versions = article.versions.all()
        version = versions[0]
        assert version.next == versions[1]
        assert version.next.next == versions[2]

    def test_index_for_deleted_parent(self, session, versioning_options):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        session.delete(article)
        session.commit()

        versions = session.scalars(
            sa.select(self.ArticleVersion).order_by(
                getattr(self.ArticleVersion, versioning_options["transaction_column_name"])
            )
        ).all()
        assert versions[0].index == 0
        assert versions[1].index == 1

    def test_index_for_live_parent(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        assert article.versions[0].index == 0


class VersionModelAccessorsWithCompositePkTestCase(TestCase):
    def create_models(self, decl_base, versioning_options):
        class User(decl_base):
            __tablename__ = "user"
            __versioned__ = copy(versioning_options)

            first_name = sa.Column(sa.Unicode(255), primary_key=True)
            last_name = sa.Column(sa.Unicode(255), primary_key=True)
            email = sa.Column(sa.Unicode(255))

        self.User = User

    def test_previous_two_versions(self, session):
        user = self.User(
            first_name="Some user",
            last_name="Some last_name",
        )
        session.add(user)
        session.commit()
        user2 = self.User(
            first_name="Second user",
            last_name="Second user",
        )
        session.add(user2)
        session.commit()

        user.email = "Updated email"
        session.commit()
        user.email = "Updated email 2"
        session.commit()

        assert user.versions[2].previous
        assert user.versions[1].previous
        assert user.versions[2].previous == user.versions[1]
        assert user.versions[1].previous == user.versions[0]

    def test_next_two_versions(self, session):
        user = self.User()
        user.first_name = "Some user"
        user.last_name = "Some last_name"
        session.add(user)
        session.commit()
        user2 = self.User()
        user2.first_name = "Second user"
        user2.last_name = "Second user"
        session.add(user2)
        session.commit()

        user.email = "Updated user"
        session.commit()
        user.email = "Updated user 2"
        session.commit()

        assert user.versions[0].next
        assert user.versions[1].next
        assert user.versions[0].next == user.versions[1]
        assert user.versions[1].next == user.versions[2]


create_test_cases(VersionModelAccessorsTestCase)
create_test_cases(VersionModelAccessorsWithCompositePkTestCase)
