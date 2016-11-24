// Javascript to enable link to tab
var url = document.location.toString();
if (url.match('#')) {
    $('.nav-tabs a[href="#' + url.split('#')[1] + '"]').tab('show');
    $('.nav-pills a[href="#' + url.split('#')[1] + '"]').tab('show');
}

can = {}

can.dom = {}

can.dom.html = function (obj) {
    var tmp = $('<div/>').html(obj);
    return tmp.html();
}

can.dom.create_link = function (href, label, title) {

    var a = $('<a/>').attr('href', href).text(label);

    if (href.substr(0, 4) == 'http') {
        a.attr('target', '_blank')
    }

    if (title !== undefined) {
        a.attr('title', title).attr('data-toggle', 'tooltip')
    }

    return a;
}

can.dom.link = function (href, label, title) {
    return can.dom.html(can.dom.create_link(href, label, title));
}

can.dom.create_label = function (content, title, type, pad) {

    if (type === undefined) {
        type = 'default';
    }

    return $('<span/>').addClass('label label-' + type)
        .attr('title', title).text(content)
        .attr('data-toggle', 'tooltip');
}

can.dom.label = function (content, title, type) {
    return can.dom.html(can.dom.create_label(content, title, type));
}

can.dom.create_span = function (content, title) {
    return $('<span/>').attr('title', title).text(content)
        .attr('data-toggle', 'tooltip');
}

can.dom.span = function (content, title) {
    return can.dom.html(can.dom.create_span(content, title).tooltip());
}

can.dom.user_status = function (user) {
    var category = 'success';
    if (user.status.id == 0) {
        category = 'warning';
    } else if (user.status.id == 2) {
        category = 'danger';
    }
    return can.dom.label(user.status.name, undefined, category);
}

can.dom.datetime = function (data) {
    if (data) {
        var date = moment(data);
        return can.dom.html($('<time/>').attr('title', date.format('MMMM D YYYY h:mm A')).text(date.fromNow()))
    }
}

can.dom.create_progress = function (num, den) {
    var percent = parseInt(num / den * 100) + '%';
    return $('<div/>').addClass('progress').append(
        $('<div/>').addClass('progress-bar progress-bar-success')
            .css('min-width', '2em').css('width', percent)
            .text(percent)
            .attr('title', num + ' of ' + den)
    )
}

can.dom.progress = function (num, den) {
    return can.dom.html(can.dom.create_progress(num, den))
}

can.dom.create_yesno_bar = function (yes, no, total) {
    var $progress = $('<div/>').addClass('progress');
    if (yes > 0) {
        var percent = parseInt(yes / total * 100) + '%';
        $progress.append($('<div/>').addClass('progress-bar progress-bar-success')
            .css('min-width', '2em').css('width', percent)
            .text(percent + " Yes")
            .attr('title', yes + ' of ' + total));
    }
    if (no > 0) {
        var percent = parseInt(no / total * 100) + '%';
        $progress.append($('<div/>').addClass('progress-bar progress-bar-danger')
            .css('min-width', '2em').css('width', percent)
            .text(percent + " No")
            .attr('title', no + ' of ' + total));
    }
    return $progress;
}

can.dom.yesno_bar = function (yes, no, total) {
    return can.dom.html(can.dom.create_yesno_bar(yes, no, total))
}

$(document).ready(function () {

    // enable links to tab
    var hash = document.location.hash;
    if (hash) {
        $('.nav-tabs a[href=' + hash + '-pane]').tab('show');
    }

    // enable form validator inside tabs
    $('a[data-toggle="tab"]').one('shown.bs.tab', function (e) {
        $($(e.target).attr('href')).find('form').validator();
    });

    // enable data-moment
    $('time[data-moment]').each(function (i, time) {
        var data = moment($(time).attr('data-moment'));
        $(time).html(data.fromNow()).attr('title', data.format('MMMM D YYYY h:mm A')).addClass('tip-auto').tooltip();
    });

    // enable fancy tooltips
    $('[data-toggle="tooltip"]').addClass('tip-auto').tooltip();

    // enable ajax csrf token
    $.ajaxSetup({
        headers: {'X-CSRFToken': $('meta[name=csrf-token]').attr('content')}
    });

    /************************
     * ajax processing indicator *
     ************************/

    $('#processing-indicator').popup({
        transition: 'all 0.5s',
        blur: false,
        escape: false
    }).removeClass('invisible');

    $.ajaxSetup({
        global: true,
        xhr: function () {
            var xhr = new window.XMLHttpRequest();
            xhr.addEventListener("progress", function (e) {
                if (e.lengthComputable) {
                    var pct = Math.ceil((e.loaded || e.position) / e.total * 100);
                    $('.progress-bar').css('width', pct + '%')
                        .text(pct + '%')
                        .attr('aria-valuenow', pct);
                }
            }, false);
            return xhr;
        }
    });

    $(document).ajaxSend(function () {
        $('#processing-indicator div.progress-bar').css('width', 0).text('0%').attr('aria-valuenow', 0);
        $('#processing-indicator').popup('show');
    });

    $(document).ajaxStop(function () {
        $('#processing-indicator').delay(100).animate({opacity: 0}, {
            duration: 100, complete: function () {
                $('#processing-indicator').popup('hide');
            }
        });
    });

});
