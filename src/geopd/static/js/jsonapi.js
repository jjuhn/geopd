jsonapi = {}

jsonapi.make_resource = function (api_type, id, attributes, relationships) {
    var resource_object = {type: api_type};
    if (id != undefined) {
        resource_object.id = id;
    }
    if (attributes != undefined) {
        resource_object.attributes = attributes;
    }
    if (relationships != undefined) {
        resource_object.relationships = relationships;
    }
    return {data: resource_object};
}

jsonapi.parse_response = function (json) {

    var data = null;
    var included = {};

    function _parse_resource_object(data) {
        var obj = (data.attributes != undefined) ? data.attributes : {};
        obj.id = data.id;
        for (var attr in data.relationships) {
            var relation = data.relationships[attr].data;
            if (relation.id == undefined) {
                obj[attr] = [];
                if (relation[0] != undefined && relation[0].type in included) {
                    for (var j = 0; j < relation.length; j++) {
                        var item = included[relation[j].type][relation[j].id];
                        item.id = relation[j].id;
                        obj[attr].push(item);
                    }
                } else {
                    for (var j = 0; j < relation.length; j++) {
                        obj[attr].push(relation[j]);
                    }
                }
            } else {
                if (relation.type in included) {
                    obj[attr] = included[relation.type][relation.id];
                    obj[attr].id = relation.id;
                } else {
                    obj[attr] = relation;
                }
            }
        }
        return obj;
    }

    // parse included object
    if (json.included != undefined) {
        for (var i = json.included.length - 1; i >= 0; i--) {
            var row = json.included[i];
            if (included[row.type] == undefined) {
                included[row.type] = {};
            }
            included[row.type][row.id] = (row.attributes == undefined) ? {} : row.attributes;
            included[row.type][row.id].id = row.id;
            for (var attr in row.relationships) {
                var relation = row.relationships[attr].data;
                if ($.isArray(relation)) {
                    included[row.type][row.id][attr] = [];
                    for (var j = 0; j < relation.length; j++) {
                        if (included[relation[j].type] != undefined &&
                            included[relation[j].type][relation[j].id] != undefined) {
                            var obj = included[relation[j].type][relation[j].id];
                            obj.id = relation[j].id;
                            included[row.type][row.id][attr].push(obj);
                        } else {
                            included[row.type][row.id][attr].push(relation[j]);
                        }
                    }
                } else {
                    if (included[relation.type] != undefined &&
                        included[relation.type][relation.id] != undefined) {
                        var obj = included[relation.type][relation.id];
                        obj.id = relation.id;
                        included[row.type][row.id][attr] = obj;
                    } else {
                        included[row.type][row.id][attr] = relation;
                    }
                }
            }
        }
    }


    // parse data object
    if ($.isArray(json.data)) {
        // collection
        data = [];
        for (var i = 0; i < json.data.length; i++) {
            data.push(_parse_resource_object(json.data[i]));
        }
    } else {
        // single resource
        data = _parse_resource_object(json.data);
    }

    return data;
};