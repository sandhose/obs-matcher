import restless.exceptions
from restless.preparers import SubPreparer, CollectionSubPreparer

from .utils import AutoPreparer, CustomFlaskResource
from ..scheme.platform import Platform, PlatformGroup, Scrap, ScrapStatus
from .. import db


class PlatformGroupResource(CustomFlaskResource):
    preparer = AutoPreparer({
        'name': 'name',
        'platforms': CollectionSubPreparer('platforms', AutoPreparer({
            'name': 'name',
            'slug': 'slug',
            'country': 'country',
        })),
    })

    def is_authenticated(self):
        return True

    def list(self):
        return PlatformGroup.query.all()

    def detail(self, pk):
        try:
            return PlatformGroup.query.filter(PlatformGroup.id == pk).one()
        except:
            raise restless.exceptions.NotFound()

    def create(self):
        group = PlatformGroup(self.data['name'])
        if 'platforms' in self.data:
            for platform in self.data['platforms']:
                pid = platform['id'] if isinstance(platform, dict) \
                    else platform

                try:
                    group.platforms.append(Platform.query.filter(
                        Platform.id == pid).one())
                except:
                    raise restless.exceptions.BadRequest()

        db.session.add(group)
        db.session.commit()
        return group

    def delete(self, pk):
        try:
            group = PlatformGroup.query.filter(PlatformGroup.id == pk).one()
        except:
            raise restless.exceptions.NotFound()

        db.session.delete(group)
        db.session.commit()

    def update(self, pk):
        try:
            group = PlatformGroup.query.filter(PlatformGroup.id == pk).one()
        except:
            raise restless.exceptions.NotFound()

        if 'name' in self.data:
            group.name = self.data['name']

        db.session.commit()
        return group


class PlatformResource(CustomFlaskResource):
    preparer = AutoPreparer({
        'name': 'name',
        'slug': 'slug',
        'url': 'url',
        'country': 'country',
        'max_rating': 'max_rating',
        'base_score': 'base_score',
        'group': SubPreparer('group', AutoPreparer({
            'name': 'name',
        })),
    })

    def is_authenticated(self):
        return True

    def list(self):
        return Platform.query.all()

    def detail(self, pk):
        try:
            return Platform.query.filter(Platform.id == pk).one()
        except:
            raise restless.exceptions.NotFound()

    def create(self):
        if 'group' in self.data:
            gid = self.data['group']['id'] \
                if isinstance(self.data['group'], dict) \
                else self.data['group']

            try:
                self.data['group'] = PlatformGroup.query.filter(
                    PlatformGroup.id == gid)
            except:
                raise restless.exceptions.NotFound()

        platform = Platform(**self.data)
        db.session.add(platform)
        db.session.commit()
        return platform

    def update(self, pk):
        try:
            platform = Platform.query.filter(Platform.id == pk).one()
        except:
            raise restless.exceptions.NotFound()

        if 'group' in self.data:
            gid = self.data['group']['id'] \
                if isinstance(self.data['group'], dict) \
                else self.data['group']

            try:
                platform.group = PlatformGroup.query.filter(
                    PlatformGroup.id == gid)
            except:
                raise restless.exceptions.NotFound()

        if 'name' in self.data:
            platform.name = self.data['name']
        if 'slug' in self.data:
            platform.name = self.data['slug']
        if 'url' in self.data:
            platform.url = self.data['url']
        if 'country' in self.data:
            platform.country = self.data['country']
        if 'max_rating' in self.data:
            platform.max_rating = self.data['max_rating']
        if 'base_score' in self.data:
            platform.base_score = self.data['base_score']

        db.session.commit()
        return platform


class ScrapResource(CustomFlaskResource):
    preparer = AutoPreparer({
        'status': 'status',
        'date': 'date',
        'platform': SubPreparer('platform', AutoPreparer({
            'name': 'name',
        })),
    })

    def is_authenticated(self):
        return True

    def list(self):
        return Scrap.query.all()

    def detail(self, pk):
        return Scrap.query.filter(Scrap.id == pk).one()

    def update(self, pk):
        scrap = Scrap.query.filter(Scrap.id == pk).one()

        if 'status' in self.data:
            status = ScrapStatus.from_name(self.data['status'])
            scrap.to_status(status)

        db.session.commit()

        return scrap

    def create(self):
        try:
            platform = Platform.lookup(self.data['platform'])
        except:
            raise restless.exceptions.BadRequest('Missing key `platform`')

        if platform is None:
            raise restless.exceptions.NotFound('platform not found')

        scrap = Scrap(platform=platform)
        scrap.status = ScrapStatus.SCHEDULED

        if 'status' in self.data:
            status = ScrapStatus.from_name(self.data['status'])
            scrap.to_status(status)

        db.session.add(scrap)
        db.session.commit()
        return scrap
