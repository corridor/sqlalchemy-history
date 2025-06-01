import pytest
import sqlalchemy as sa

from sqlalchemy_history import versioning_manager
from tests import TestCase


class TestBeforeFlushListener(TestCase):
    @pytest.fixture(autouse=True)
    def setup_method_to_modify_listner(self, setup_session):
        @sa.event.listens_for(sa.orm.Session, "before_flush")
        def before_flush(session, ctx, instances):
            for obj in session.dirty:
                obj.name = "Updated article"

        self.before_flush = before_flush

        self.article = self.Article()
        self.article.name = "Some article"
        self.article.content = "Some content"
        self.session.add(self.article)
        self.session.commit()

        yield
        self.session.expunge(self.article)
        del self.article
        sa.event.remove(sa.orm.Session, "before_flush", self.before_flush)

    def test_manual_tx_creation_with_no_actual_changes(self):
        self.article.name = "Some article"

        uow = versioning_manager.unit_of_work(self.session)
        uow.create_transaction(self.session)
        self.session.flush()
