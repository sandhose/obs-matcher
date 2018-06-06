import sqlalchemy.orm.exc

import restless.exceptions
from restless.preparers import CollectionSubPreparer, SubPreparer

from ..app import db
from ..scheme.platform import (Platform, PlatformGroup, PlatformType, Scrap,
                               ScrapStatus,)
from .utils import AutoPreparer, CustomFlaskResource


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
        except sqlalchemy.orm.exc.NoResultFound:
            raise restless.exceptions.NotFound()

    def create(self):
        id = db.session.query(PlatformGroup.id)\
            .filter(PlatformGroup.name == self.data['name'])\
            .first()
        group = db.session.merge(PlatformGroup(id=id, name=self.data['name']))
        if 'platforms' in self.data:
            for platform in self.data['platforms']:
                pid = platform['id'] if isinstance(platform, dict) \
                    else platform

                try:
                    group.platforms.append(Platform.query.filter(
                        Platform.id == pid).one())
                except sqlalchemy.orm.exc.NoResultFound:
                    raise restless.exceptions.BadRequest()

        db.session.add(group)
        db.session.commit()
        return group

    def delete(self, pk):
        try:
            group = PlatformGroup.query.filter(PlatformGroup.id == pk).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise restless.exceptions.NotFound()

        db.session.delete(group)
        db.session.commit()

    def update(self, pk):
        try:
            group = PlatformGroup.query.filter(PlatformGroup.id == pk).one()
        except sqlalchemy.orm.exc.NoResultFound:
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
        except sqlalchemy.orm.exc.NoResultFound:
            raise restless.exceptions.NotFound()

    def create(self):
        # Create or update platform
        if 'group' in self.data:
            gid = self.data['group']['id'] \
                if isinstance(self.data['group'], dict) \
                else self.data['group']

            try:
                group = PlatformGroup.query\
                    .filter(PlatformGroup.id == gid)\
                    .one()
            except sqlalchemy.orm.exc.NoResultFound:
                raise restless.exceptions.NotFound()
            self.data['group'] = None
        else:
            group = None

        if 'type' in self.data:
            self.data['type'] = PlatformType.from_name(self.data['type'])

        if 'slug' in self.data:
            self.data['id'] = db.session\
                .query(Platform.id)\
                .filter(Platform.slug == self.data['slug'])\
                .first()

        platform = db.session.merge(Platform(**self.data))
        platform.group = group
        db.session.add(platform)
        db.session.commit()

        return platform

    def update(self, pk):
        try:
            platform = Platform.query.filter(Platform.id == pk).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise restless.exceptions.NotFound()

        if 'group' in self.data:
            gid = self.data['group']['id'] \
                if isinstance(self.data['group'], dict) \
                else self.data['group']

            try:
                platform.group = PlatformGroup.query.filter(
                    PlatformGroup.id == gid)
            except sqlalchemy.orm.exc.NoResultFound:
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

        if 'stats' in self.data:
            scrap.stats = self.data['stats']

        db.session.commit()

        return scrap

    def create(self):
        try:
            platform = Platform.lookup(self.data['platform'])
        except ValueError:
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
