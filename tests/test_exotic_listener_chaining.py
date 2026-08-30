import pytest
import sqlalchemy.event
from sqlalchemy.orm import Session

from sqlalchemy_history import versioning_manager
from tests import TestCase


class TestBeforeFlushListener(TestCase):
    @pytest.fixture(autouse=True)
    def setup_method_to_modify_listner(self, session):
        @sqlalchemy.event.listens_for(Session, "before_flush")
        def before_flush(session, ctx, instances):
            for obj in session.dirty:
                obj.name = "Updated article"

        self.before_flush = before_flush

        self.article = self.Article()
        self.article.name = "Some article"
        self.article.content = "Some content"
        session.add(self.article)
        session.commit()

        yield
        session.expunge(self.article)
        del self.article
        sqlalchemy.event.remove(Session, "before_flush", self.before_flush)

    def test_manual_tx_creation_with_no_actual_changes(self, session):
        self.article.name = "Some article"

        uow = versioning_manager.unit_of_work(session)
        uow.create_transaction(session)
        session.flush()
