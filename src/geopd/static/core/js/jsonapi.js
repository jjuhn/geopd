/**
 * @author Omar Zabaneh <zabano@gmail.com>
 */

var jsonapi = jsonapi || {}

jsonapi.Resource = function (type, id, attributes) {

    this.data = {type: type, attributes: {}, relationships: {}};

    if (id) this.data.id = id;
    for (key in attributes) {
        if (attributes[key]) {
            this.data.attributes[key] = attributes[key];
        }
    }

    this.relationship = function (key, data) {
        this.data.relationships[key] = {data: data};
    }

    this.jsonify = function () {
        return JSON.stringify({data: this.data});
    }
}

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
    };

    $.extend(obj, row.attributes);

    $.each(row.relationships, function (key, relationship) {
        var related = relationship.data;
        if (related) {
            if ($.isArray(related)) {
                obj[key] = [];
                if (included) {
                    $.each(related, function (i, rel) {
                        obj[key].push(included[rel.type][rel.id]);
                    });
                }
            } else {
                obj[key] = (included) ? included[related.type][related.id] : null;
            }

        } else {
            obj[key] = relationship.data;
        }
    });

    return obj;
}

jsonapi.parse_response = function (json, number_of_passes) {

    var included = {};
    var data = null;

    /**
     * parse included resources
     **/

    // parse included resources
    if (json.included) {
        for (var pass = 1; pass <= number_of_passes; pass++) {
            $.each(json.included, function (i, row) {
                if (included[row.type] == undefined) {
                    included[row.type] = {};
                }
                included[row.type][row.id] = jsonapi.parse_resource_object(row, (pass > 1) ? included : undefined);
            });
        }
    }

    /**
     * parse response data
     */

    if ($.isArray(json.data)) {  // collection
        data = [];
        $.each(json.data, function (i, row) {
            data.push(jsonapi.parse_resource_object(row, included))
        })
    } else {  // single resource
        data = jsonapi.parse_resource_object(json.data, included)
    }

    return data;
};

jsonapi.comments = function (container_id, params) {

    var BASE_URL = '/api/' + params.commentResourceType + '/';

    function reformat_comment_object(comment) {
        return {
            id: comment.id,
            created: comment['created-on'],
            modified: comment['modified-on'],
            content: comment.body,
            fullname: comment.author.name.first + ' ' + comment.author.name.last,
            profile_url: '/users/' + comment.author.id,
            profile_picture_url: '/users/' + comment.author.id + '/avatar',
            parent: (comment.parent) ? comment.parent.id : undefined,
            created_by_current_user: comment.author.id == params.userID,
        }
    };

    $(container_id).comments({

        profilePictureURL: '/users/' + params.userID + '/avatar',
        enableUpvoting: false,
        youText: params.userName,
        postCommentOnEnter: true,
        spinnerIconURL: '',
        noCommentsIconURL: '',

        timeFormatter: function (time) {
            return moment(time).fromNow();
        },

        getComments: function (success, error) {

            var url = URI(BASE_URL);
            url.addQuery('include',
                'author,author.name,parent,replies,replies.author,replies.author.name,replies.parent');
            url.addQuery('fields[users]', 'name');
            url.addQuery('fields[user-names]', 'first,last');
            url.addQuery('filter[' + params.relName + '_id.eq]', params.resourceID);

            $.ajax(url.readable(), {
                success: function (json) {
                    var comments = jsonapi.parse_response(json, 3);
                    var reformatted = [];
                    $.each(comments, function (i, comment) {
                        reformatted.push(reformat_comment_object(comment));
                        $.each(comment.replies, function (i, reply) {
                            reformatted.push(reformat_comment_object(reply));
                        });
                    });
                    success(reformatted);
                },
                error: error,
            });
        },

        postComment: function (comment, success, error) {

            var resource = jsonapi.make_resource(params.commentResourceType, null, {body: comment.content}, {
                author: {
                    data: {
                        id: params.userID,
                        type: 'users'
                    }
                }
            });

            if (comment.parent) {
                var parent_id = $('li.comment[data-id=' + comment.parent + ']').parents('li.comment').attr('data-id');
                if (parent_id == undefined) parent_id = comment.parent;
                resource['data']['relationships']['parent'] = {
                    data: {
                        type: params.commentResourceType,
                        id: parent_id
                    }
                }
            } else {
                resource['data']['relationships'][params.relName.replace('_', '-')] = {
                    data: {
                        type: params.resourceType,
                        id: params.resourceID,
                    }
                }
            }

            var url = URI(BASE_URL)
            url.addQuery('include', 'author,author.name,parent');
            url.addQuery('fields[users]=name');
            url.addQuery('fields[user-names]=first,last');
            $.ajax(url.readable(), {
                type: 'post',
                data: JSON.stringify(resource),
                contentType: "application/json",
                success: function (json) {
                    var comment = jsonapi.parse_response(json, 2);
                    success(reformat_comment_object(comment));
                },
                error: error,
            });
        },

        putComment: function (comment, success, error) {

            var resource = jsonapi.make_resource(params.commentResourceType, comment.id, {body: comment.content});
            var url = URI(BASE_URL + comment.id);
            url.addQuery('include', 'author,author.name,parent');
            url.addQuery('fields[users]=name');
            url.addQuery('fields[user-names]=first,last');
            $.ajax(url.readable(), {
                type: 'patch',
                data: JSON.stringify(resource),
                contentType: "application/json",
                success: function (json) {
                    var comment = jsonapi.parse_response(json, 2);
                    success(reformat_comment_object(comment));
                },
                error: error,
            });
        },

        deleteComment: function (comment, success, error) {

            var url = URI(BASE_URL + comment.id);
            $.ajax({
                type: 'delete',
                url: url.readable(),
                success: success,
                error: error
            });
        }

    });
}