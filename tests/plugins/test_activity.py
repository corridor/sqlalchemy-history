import importlib_metadata
import pytest
import sqlalchemy as sa

from sqlalchemy_history import versioning_manager
from sqlalchemy_history.plugins import ActivityPlugin
from tests import QueryPool, TestCase


class ActivityTestCase(TestCase):
    plugins = [ActivityPlugin()]

    def create_models(self):
        TestCase.create_models(self)

        class User(self.Model):
            __tablename__ = "user"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)

        self.User = User

    def create_article(self, session):
        article = self.Article(name="Some article")
        session.add(article)
        return article

    def create_activity(self, session, object_=None, target=None):
        activity = versioning_manager.activity_cls(
            object=object_,
            target=target,
            verb="create",
        )
        session.add(activity)
        return activity


# ref : https://github.com/kvesteri/sqlalchemy-utils/issues/719
@pytest.mark.skipif(
    importlib_metadata.version("sqlalchemy").startswith("2."),
    reason="sqla-utils generic relations has issue with sqla 2.x",
)
class TestActivityNotId(ActivityTestCase):
    def create_models(self):
        TestCase.create_models(self)

        class NotIdModel(self.Model):
            __tablename__ = "not_id"
            __versioned__ = {"base_classes": (self.Model,)}

            pk = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)

        self.NotIdModel = NotIdModel

    def test_create_activity_with_pk(self, session):
        not_id_model = self.NotIdModel(name="Some model without id PK")
        session.add(not_id_model)
        session.commit()
        self.create_activity(session, not_id_model)
        session.commit()
        activity = session.scalars(sa.select(versioning_manager.activity_cls)).first()
        assert activity
        assert activity.transaction_id
        assert activity.object == not_id_model
        assert activity.object_version == not_id_model.versions.all()[-1]


# ref : https://github.com/kvesteri/sqlalchemy-utils/issues/719
@pytest.mark.skipif(
    importlib_metadata.version("sqlalchemy").startswith("2."),
    reason="sqla-utils generic relations has issue with sqla 2.x",
)
class TestActivity(ActivityTestCase):
    def test_creates_activity_class(self):
        assert versioning_manager.activity_cls.__name__ == "Activity"

    def test_create_activity(self, session):
        article = self.create_article(session)
        session.flush()
        self.create_activity(session, article)
        session.commit()
        activity = session.scalars(sa.select(versioning_manager.activity_cls)).first()
        assert activity
        assert activity.transaction_id
        assert activity.object == article
        assert activity.object_version == article.versions.all()[-1]

    def test_delete_activity(self, session):
        article = self.create_article(session)
        self.create_activity(session, article)
        session.commit()
        session.delete(article)
        activity = versioning_manager.activity_cls(
            object=article,
            verb="delete",
        )
        session.add(activity)
        session.commit()
        versions = session.scalars(
            sa.select(self.ArticleVersion).order_by(sa.desc(self.ArticleVersion.transaction_id))
        ).all()
        assert activity
        assert activity.transaction_id
        assert activity.object is None
        assert activity.object_version == versions[-1]

    def test_activity_queries(self, session):
        article = self.create_article(session)
        session.flush()
        self.create_activity(session, article)
        session.commit()
        tag = self.Tag(name="some tag")
        session.add(tag)
        tag.article = article
        session.flush()
        Activity = versioning_manager.activity_cls
        activity = Activity(
            object=tag,
            target=article,
            verb="create",
        )
        session.add(activity)
        session.commit()
        activities = session.scalars(
            sa.select(Activity).filter(sa.or_(Activity.object == article, Activity.target == article))
        )
        assert activities.count() == 2


# ref : https://github.com/kvesteri/sqlalchemy-utils/issues/719
@pytest.mark.skipif(
    importlib_metadata.version("sqlalchemy").startswith("2."),
    reason="sqla-utils generic relations has issue with sqla 2.x",
)
class TestObjectTxIdGeneration(ActivityTestCase):
    def test_does_not_query_db_if_version_obj_in_session(self, session):
        article = self.create_article(session)
        session.flush()
        self.create_activity(session, object=article)
        query_count = len(QueryPool.queries)
        session.commit()
        assert query_count + 1 == len(QueryPool.queries)

    def test_create_activity_with_multiple_existing_objects(self, session):
        article = self.create_article(session)
        session.commit()
        self.create_article(session)
        session.commit()
        activity = self.create_activity(session, article)
        session.commit()
        assert activity
        assert activity.transaction_id
        assert activity.object == article
        assert activity.object_version == article.versions.all()[-1]


# ref : https://github.com/kvesteri/sqlalchemy-utils/issues/719
@pytest.mark.skipif(
    importlib_metadata.version("sqlalchemy").startswith("2."),
    reason="sqla-utils generic relations has issue with sqla 2.x",
)
class TestTargetTxIdGeneration(ActivityTestCase):
    def test_does_not_query_db_if_version_obj_in_session(self, session):
        article = self.create_article(session)
        session.flush()
        self.create_activity(session, target=article)
        query_count = len(QueryPool.queries)
        session.commit()
        assert query_count + 1 == len(QueryPool.queries)

    def test_with_multiple_existing_targets(self, session):
        article = self.create_article(session)
        session.commit()
        self.create_article(session)
        session.commit()
        activity = self.create_activity(session, target=article)
        session.commit()
        assert activity
        assert activity.transaction_id
        assert activity.target == article
        assert activity.target_version == article.versions.all()[-1]

    def test_activity_target(self, session):
        article = self.create_article(session)
        self.create_activity(session, article)
        session.commit()
        tag = self.Tag(name="some tag")
        session.add(tag)
        tag.article = article
        session.flush()
        activity = versioning_manager.activity_cls(
            object=tag,
            target=article,
            verb="create",
        )
        session.add(activity)
        session.commit()
        activity = session.scalars(sa.select(versioning_manager.activity_cls).filter_by(id=activity.id)).one()
        assert activity
        assert activity.transaction_id
        assert activity.object == tag
        assert activity.object_version == tag.versions.all()[-1]
        assert activity.target == article
        assert activity.target_version == article.versions.all()[-1]
