from flask_sqlalchemy import SQLAlchemy
from injector import inject
from matcher.scheme.platform import Platform, PlatformGroup, PlatformType
from matcher.test import TestCase


class PlatformTest(TestCase):
    @inject
    def test_list(self, db: SQLAlchemy):
        response = self.client.get("/api2/platforms/")
        self.assertEqual(response.json["items"], [])

        platform = Platform(name='foo', slug='bar', type=PlatformType.INFO, country='US')
        db.session.add(platform)
        db.session.commit()
        response = self.client.get("/api2/platforms/")
        self.assertEqual(response.json["items"], [{
            'id': platform.id,
            'type': 'info',
            'slug': platform.slug,
            'name': platform.name,
            'country': platform.country,
            'group': None
        }])

    @inject
    def test_create(self, db: SQLAlchemy):
        response = self.client.post("/api2/platforms/", data={
            'type': 'info',
            'slug': 'bar',
            'name': 'foo',
            'country': 'US',
        })

        assert 'id' in response.json

        platform = db.session.query(Platform).get(response.json['id'])
        assert platform is not None
        assert platform.id == response.json['id']
        assert platform.type == PlatformType.INFO
        assert platform.slug == 'bar'
        assert platform.name == 'foo'
        assert platform.country == 'US'
        assert platform.group is None

        # slug should be unique
        response = self.client.post("/api2/platforms/", data={
            'type': 'info',
            'slug': 'bar',
            'name': 'baz',
            'country': 'US',
        })

        # FIXME: should be a 400
        self.assert500(response)

        # invalid type
        response = self.client.post("/api2/platforms/", data={
            'type': 'foo',
            'slug': 'bar2',
            'name': 'foo2',
            'country': 'US',
        })

        self.assert400(response)

    @inject
    def test_get(self, db: SQLAlchemy):
        platform = Platform(name='foo', slug='bar', type=PlatformType.INFO, country='US')
        db.session.add(platform)
        db.session.commit()

        response = self.client.get("/api2/platforms/{}".format(platform.id))
        self.assertEqual(response.json, {
            'id': platform.id,
            'type': 'info',
            'slug': platform.slug,
            'name': platform.name,
            'country': platform.country,
            'group': None
        })

        group = PlatformGroup(name='baz', platforms=[platform])
        db.session.add(group)
        db.session.commit()

        response = self.client.get("/api2/platforms/{}".format(platform.id))
        self.assertEqual(response.json['group'], {
            'id': group.id,
            'name': group.name,
        })

    @inject
    def test_delete(self, db: SQLAlchemy):
        platform = Platform(name='foo', slug='bar', type=PlatformType.INFO, country='US')
        db.session.add(platform)
        db.session.commit()

        platform_id = platform.id
        db.session.expire(platform)

        response = self.client.delete("/api2/platforms/{}".format(platform.id))
        assert response.json == 'ok'

        assert db.session.query(PlatformGroup).get(platform_id) is None

    @inject
    def test_put(self, db: SQLAlchemy):
        platform = Platform(name='foo', slug='bar', type=PlatformType.INFO, country='US')
        db.session.add(platform)
        db.session.commit()

        response = self.client.put("/api2/platforms/{}".format(platform.id), data={'name': 'baz'})
        assert response.json['name'] == 'baz'

        db.session.refresh(platform)
        assert platform.name == 'baz'
