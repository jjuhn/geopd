from datetime import datetime

from flask import jsonify
from flask import request
from flask import url_for
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy_utils import get_primary_keys
from sqlalchemy_utils import get_query_entities
from sqlalchemy_utils import get_type

from geopd.orm import Base
from geopd.orm import db
from geopd.util import to_underscore


########################################################################################################################
# constants
########################################################################################################################


JSONAPI_MEDIA_TYPE = 'application/vnd.api+json'


########################################################################################################################
# exceptions
########################################################################################################################


class JSONAPIError(Exception):
    pass


########################################################################################################################
# api registry
########################################################################################################################


_registry = {}  #: holds json resource ORM classes

for cls in Base._decl_class_registry.values():
    if hasattr(cls, '__jsonapi_type__'):
        if cls.__jsonapi_type__ in _registry.keys():
            raise JSONAPIError("duplicate JSON api type: '{0}'".format(cls.__jsonapi_type__))
        _registry[cls.__jsonapi_type__] = cls


########################################################################################################################
# helper classes
########################################################################################################################


class IncludedObjects(object):
    def __init__(self):
        self._objs = dict()
        self._index = 0
        self._sorted = []

    def add(self, obj, level):
        if isinstance(obj, Base):
            key = obj.__jsonapi_type__, getattr(obj, obj.__jsonapi_id__ if hasattr(obj, '__jsonapi_id__') else 'id')
            self._objs[key] = (level, obj)
            self._sorted = [o for level, o in sorted(self._objs.values())]

    def __iter__(self):
        return self

    def next(self):
        try:
            res = self._sorted[self._index]
        except IndexError:
            self._index = 0  # reset index
            raise StopIteration
        else:
            self._index += 1
            return res


class JSONResponse(object):
    def __init__(self, query):
        """
        :param Query query: SQLAlchemy query object
        """

        self._query = query
        self._cls = get_query_entities(query)[0]
        self._fields = dict()  #: holds sparse fields from url query string keyed by api type
        self._included = list()  #: holds include fields and their associated ORM classes

        self._included_objs = IncludedObjects()  #: holds included ORM objects (no duplicates)

        self._parse_url_query_string()
        self._optimize_sql_query()
        self.document = dict(
            self=url_for(request.endpoint, **request.view_args)
        )

    @staticmethod
    def _get_key_column_name(obj):
        return obj.__jsonapi_id__ if hasattr(obj, '__jsonapi_id__') else 'id'

    @staticmethod
    def _get_attribute(obj, attr):
        value = getattr(obj, attr)
        if isinstance(value, datetime):
            return value.isoformat() + 'Z'
        else:
            return value

    def _optimize_sql_query(self):

        join_paths = self._included[:]  # copy list

        for path in self._included:
            cls = self._cls
            for attr in path.split('.'):
                prop = getattr(cls, attr)
                cls = get_type(prop.remote_attr if isinstance(prop, AssociationProxy) else prop)
            if cls.__jsonapi_type__ in self._fields:
                for attr in self._fields[cls.__jsonapi_type__]:
                    prop = inspect(cls).attrs[attr]
                    if isinstance(prop, RelationshipProperty):
                        join_paths.append("{0}.{1}".format(path, attr))

        join_paths = sorted(list(set(join_paths)))  # remove duplicates

        if join_paths:
            expanded_paths = [[]]
            prefix = join_paths[0]
            index = 0
            for attr in join_paths:
                if attr.startswith(prefix):
                    expanded_paths[index].append(attr)
                else:
                    expanded_paths.append([attr])
                    index += 1
                prefix = attr

            for paths in expanded_paths:
                props = []
                for attr_path in paths:
                    for prop in self._get_properties(attr_path):
                        props.append(prop)
                    if props:
                        loader = joinedload(props[0])
                        for prop in props[1:]:
                            loader = loader.joinedload(prop)
                        self._query = self._query.options(loader)

    def _get_properties(self, attr_path):
        cls = self._cls
        res = tuple()
        for attr in attr_path.split('.'):
            prop = getattr(cls, attr)
            if isinstance(prop, AssociationProxy):
                cls = get_type(prop.remote_attr)
                res = prop.local_attr, prop.remote_attr
            else:
                cls = get_type(prop)
                res = prop,
        return res

    def _parse_url_query_string(self):

        inc = request.args.get('included')
        if inc:
            self._included = inc.split(',')

        for key, value in request.args.items():
            if key.startswith('fields'):
                api_type = ''.join([c for c in key.replace('fields', '') if c.isalpha() or c == '-'])
                self._fields[api_type] = value.split(',')

    def _render_property(self, obj):
        if not obj:
            return None

        attrs = dict()
        for prop in inspect(obj.__class__).attrs:
            if prop.key in obj.__jsonapi_fields__:
                if isinstance(prop, ColumnProperty):
                    attrs[prop.key] = self._get_attribute(obj, prop.key)
                elif isinstance(prop, RelationshipProperty):
                    if prop.uselist:
                        value = getattr(obj, prop.key)
                        attrs[prop.key] = [self._render_property(x) for x in value] if value else []
                    else:
                        attrs[prop.key] = self._render_property(getattr(obj, prop.key))
        return attrs

    def _render_resource(self, obj, reference=False, included=False):

        api_type = obj.__jsonapi_type__
        key_column_name = self._get_key_column_name(obj)
        resource_id = str(getattr(obj, key_column_name))
        data = dict(id=resource_id, type=api_type)

        if reference:
            return data

        endpoint = 'api.get_{0}'.format(to_underscore(_registry[api_type].__name__))
        view_args = dict([(key_column_name, resource_id)]) if hasattr(obj, 'id') \
            else dict([(k, getattr(obj, k)) for k in get_primary_keys(obj).keys()])

        if hasattr(obj.__class__, '__jsonapi_parent__'):
            parent = getattr(obj, api_type.split('-')[0])
            key = self._get_key_column_name(parent)
            view_args[key] = getattr(parent, key)

        data['attributes'] = dict()
        data['relationships'] = dict()
        data['links'] = dict(self=url_for(endpoint, **view_args))

        # fetch fields to display from `fields` query parameters
        attrs = []
        if api_type in self._fields.keys():
            for attr in self._fields[api_type]:
                attrs.append((attr, attr))
        else:
            for attr in obj.__jsonapi_fields__:
                attrs.append((attr, attr))

        # fetch additional fields to display from the `included` query parameter
        included_types = list()
        for attr_path in self._included:
            attr = attr_path.split('.')[-1]
            if hasattr(obj, attr):
                prop = getattr(obj.__class__, attr)
                if isinstance(prop, AssociationProxy):
                    prop = prop.remote_attr
                included_types.append(get_type(prop))
                if attr not in attrs:
                    attrs.append((attr, attr_path))

        # render fields (recursively)
        for attr, attr_path in attrs:
            prop = getattr(obj.__class__, attr)
            if isinstance(prop, InstrumentedAttribute):
                prop = prop.prop
            cls = get_type(prop.remote_attr if isinstance(prop, AssociationProxy) else prop)
            if isinstance(obj, Base) and hasattr(cls, '__jsonapi_type__'):
                data['relationships'][attr] = dict()
                if isinstance(prop, AssociationProxy):
                    values = [getattr(o, prop.remote_attr.key) for o in getattr(obj, prop.local_attr.key)]
                    data['relationships'][attr]['data'] = [self._render_resource(x, reference=True) for x in values] \
                        if values else []
                elif prop.uselist:
                    values = getattr(obj, attr)
                    data['relationships'][attr]['data'] = [self._render_resource(x, reference=True) for x in values] \
                        if values else []
                else:
                    data['relationships'][attr]['data'] = self._render_resource(getattr(obj, attr), reference=True)
                if cls in included_types:
                    value = getattr(obj, attr)
                    level = attr_path.count('.')
                    try:
                        for o in value:
                            self._included_objs.add(o, level)
                    except TypeError:
                        self._included_objs.add(value, level)

            else:
                if isinstance(prop, ColumnProperty):
                    data['attributes'][attr] = self._get_attribute(obj, attr)
                elif isinstance(prop, RelationshipProperty):
                    if prop.uselist:
                        value = getattr(obj, attr)
                        data['attributes'][attr] = [self._render_property(x) for x in value] if value else []
                    else:
                        data['attributes'][attr] = self._render_property(getattr(obj, attr))

        # remove empty keys
        for key in ('attributes', 'relationships'):
            if not data[key]:
                del data[key]

        return data

    def _fetch_included(self):
        self.document['included'] = [self._render_resource(inc, included=True) for inc in self._included_objs]
        if not self.document['included']:
            del self.document['included']

    def _check_json_data(self):

        if not request.json:
            raise JSONAPIError(400, 'set media type to json')

        if 'data' not in request.json.keys():
            raise JSONAPIError(400, 'request must include `data` key')

        data = request.json['data']
        if 'type' not in data.keys():
            raise JSONAPIError(400, 'request must include `type` key')

        if data['type'] != self._cls.__jsonapi_type__:
            raise JSONAPIError(400, 'invalid `type` value: "{0}"'.format(data['type']))

        if 'attributes' not in data.keys() and request.method in ['POST', 'PATCH']:
            raise JSONAPIError(400, 'request must include `attributes` key')

    def get_resource(self):
        self.document['data'] = self._render_resource(self._query.one())
        self._fetch_included()
        return jsonify(self.document)

    def get_collection(self):
        self.document['data'] = [self._render_resource(obj) for obj in self._query.all()]
        self._fetch_included()
        return jsonify(self.document)

    def add_resource(self):
        self._check_json_data()
        obj = self._cls(**request.json['data']['attributes'])
        for rel_attr, rel in request.json['data']['relationships'].items():
            resource_id, api_type = rel['data']['id'], rel['data']['type']
            cls = _registry[api_type]
            rel_obj = cls.query.filter(getattr(cls, self._get_key_column_name(cls)) == resource_id).one()
            setattr(obj, rel_attr, rel_obj)
        db.add(obj)
        try:
            db.flush()
        except SQLAlchemyError:
            db.rollback()
            raise
        self.document['data'] = self._render_resource(obj)
        self._fetch_included()
        return jsonify(self.document), 201

    def delete_resource(self):
        obj = self._query.one()
        db.delete(obj)
        try:
            db.flush()
        except SQLAlchemyError:
            db.rollback()
            raise
        return '', 204

    def patch_resource(self):
        self._check_json_data()
        data = request.json['data']
        if 'id' not in data.keys():
            raise JSONAPIError(400, 'resource patch request must include `id` key')
        key_column = getattr(self._cls, self._get_key_column_name(self._cls))
        obj = self._query.filter(key_column == data['id']).one()
        for attr, value in data['attributes'].items():
            setattr(obj, attr, value)
        try:
            db.flush()
        except SQLAlchemyError:
            db.rollback()
            raise
        self.document['data'] = self._render_resource(obj)
        self._fetch_included()
        return jsonify(self.document)


########################################################################################################################
# functions
########################################################################################################################


def get_resource(query):
    response = JSONResponse(query)
    return response.get_resource()


def get_collection(query):
    response = JSONResponse(query)
    return response.get_collection()


def add_resource(query):
    response = JSONResponse(query)
    return response.add_resource()


def delete_resource(query):
    response = JSONResponse(query)
    return response.delete_resource()


def patch_resource(query):
    response = JSONResponse(query)
    return response.patch_resource()
