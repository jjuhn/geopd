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


jsonapi.parse_resource_object = function (row, included) {

    var obj = {
        id: row.id,
        type: row.type,
    }

    $.extend(obj, row.attributes)

    if (included) {
        $.each(row.relationships, function (key, relationship) {
            related = relationship.data
            if (related != undefined) {
                if ($.isArray(related)) {
                    obj[key] = []
                    $.each(related, function(i, rel) {
                        obj[key].push(included[rel.type][rel.id])
                    });
                } else {
                    obj[key] = included[related.type][related.id]
                }

            }
        });
    }

    return obj;
}

jsonapi.parse_response = function (json) {

    var included = {};
    var data = null;

    /**
     * parse included objects and hold in temporary registry
     **/

    $.each(json.included, function (i, row) {
        if (included[row.type] == undefined) {
            included[row.type] = {};
        }
        included[row.type][row.id] = jsonapi.parse_resource_object(row);
    });

    /**
     * parse response data
     */

    if ($.isArray(json.data)) {  // collection
        data = [];
        $.each(json.data, function (i, row) {
            data.push(jsonapi.parse_resource_object(row, included))
        })
    } else {  // single resource
        data = jsonapi.parse_resource_object(row, included)
    }

    return data;
};