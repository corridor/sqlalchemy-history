from copy import copy

import sqlalchemy as sa

from sqlalchemy_history.utils import tx_column_name
from tests import create_test_cases
from tests.sqlalchemy_async import AsyncTestCase


class AsyncVersionModelAccessorsTestCase(AsyncTestCase):
    async def test_previous_for_first_version(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()

        version = (await self.versions(article))[0]
        previous_version = await version.aprevious
        assert not previous_version

    async def test_previous_for_live_parent(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()

        article.name = "Updated name"
        article.content = "Updated content"
        await self.session.commit()
        version = (await self.versions(article))[1]

        previous = await version.aprevious

        assert previous.name == "Some article"
        assert getattr(previous, tx_column_name(version)) == getattr(version, tx_column_name(version)) - 1

    async def test_previous_for_deleted_parent(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()
        await self.session.delete(article)
        await self.session.commit()

        versions = await self.ordered_versions(self.ArticleVersion)

        assert (await versions[1].aprevious).name == "Some article"

    async def test_previous_chaining(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()
        article.name = "Updated article"
        await self.session.commit()
        await self.session.delete(article)
        await self.session.commit()

        version = (await self.ordered_versions(self.ArticleVersion))[-1]

        assert await (await version.aprevious).aprevious

    async def test_previous_two_versions(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()
        article2 = self.Article(name="Second article", content="Second article")
        self.session.add(article2)
        await self.session.commit()

        article.name = "Updated article"
        await self.session.commit()
        article.name = "Updated article 2"
        await self.session.commit()

        versions = await self.versions(article)

        assert await versions[2].aprevious
        assert await versions[1].aprevious
        assert (await versions[2].aprevious) == versions[1]
        assert (await versions[1].aprevious) == versions[0]

    async def test_next_two_versions(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()
        article2 = self.Article(name="Second article", content="Second article")
        self.session.add(article2)
        await self.session.commit()

        article.name = "Updated article"
        await self.session.commit()
        article.name = "Updated article 2"
        await self.session.commit()

        versions = await self.versions(article)

        assert await versions[0].anext
        assert await versions[1].anext
        assert await versions[0].anext == versions[1]
        assert await versions[1].anext == versions[2]

    async def test_next_for_last_version(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()

        version = (await self.versions(article))[0]

        assert not await version.anext

    async def test_next_for_live_parent(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()

        article.name = "Updated name"
        article.content = "Updated content"
        await self.session.commit()
        version = (await self.versions(article))[0]

        assert (await version.anext).name == "Updated name"

    async def test_next_for_deleted_parent(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()
        version = (await self.versions(article))[0]
        await self.session.delete(article)
        await self.session.commit()
        await self.session.refresh(version)

        assert await version.anext

    async def test_chaining_next(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()
        article.name = "Updated article"
        await self.session.commit()
        article.content = "Updated content"
        await self.session.commit()

        versions = await self.versions(article)
        version = versions[0]

        assert await version.anext == versions[1]
        assert await (await version.anext).anext == versions[2]

    async def test_index_for_deleted_parent(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()

        await self.session.delete(article)
        await self.session.commit()

        versions = await self.ordered_versions(self.ArticleVersion)

        assert await versions[0].aindex == 0
        assert await versions[1].aindex == 1

    async def test_index_for_live_parent(self):
        article = self.Article(name="Some article", content="Some content")
        self.session.add(article)
        await self.session.commit()

        version = (await self.versions(article))[0]

        assert await version.aindex == 0


class AsyncVersionModelAccessorsWithCompositePkTestCase(AsyncTestCase):
    def create_models(self):
        class User(self.Model):
            __tablename__ = "user"
            __versioned__ = copy(self.options)

            first_name = sa.Column(sa.Unicode(255), primary_key=True)
            last_name = sa.Column(sa.Unicode(255), primary_key=True)
            email = sa.Column(sa.Unicode(255))

        self.User = User

    async def test_previous_two_versions(self):
        user = self.User(first_name="Some user", last_name="Some last_name")
        self.session.add(user)
        await self.session.commit()
        user2 = self.User(first_name="Second user", last_name="Second user")
        self.session.add(user2)
        await self.session.commit()

        user.email = "Updated email"
        await self.session.commit()
        user.email = "Updated email 2"
        await self.session.commit()

        versions = await self.versions(user)

        assert await versions[2].aprevious
        assert await versions[1].aprevious
        assert await versions[2].aprevious == versions[1]
        assert await versions[1].aprevious == versions[0]

    async def test_next_two_versions(self):
        user = self.User(first_name="Some user", last_name="Some last_name")
        self.session.add(user)
        await self.session.commit()
        user2 = self.User(first_name="Second user", last_name="Second user")
        self.session.add(user2)
        await self.session.commit()

        user.email = "Updated user"
        await self.session.commit()
        user.email = "Updated user 2"
        await self.session.commit()

        versions = await self.versions(user)

        assert await versions[0].anext
        assert await versions[1].anext
        assert await versions[0].anext == versions[1]
        assert await versions[1].anext == versions[2]


create_test_cases(AsyncVersionModelAccessorsTestCase)
create_test_cases(AsyncVersionModelAccessorsWithCompositePkTestCase)
