// FizzStat
// File: collect.py.js
// Desc: for Python formatting, NOT valid JS

(function() {{
    'use strict';

    var debug = {0},
        host = '{1}',
        client_key = '{2}',
        view_key = '{3}';

    if(debug) {{
        console.log('[FizzStat]', 'host: ' + host);
        console.log('[FizzStat]', 'client key: ' + client_key);
        console.log('[FizzStat]', 'view key: ' + view_key);
    }}

    var event = function(event_type, value, data, callback) {{
        // Make new ajax request to /event/<view_key>/<event_type>, async & set json
        var request = new XMLHttpRequest();
        request.open('POST', '//' + host + '/event/' + view_key + '/' + event_type, true);
        request.setRequestHeader('Content-type', 'application/json');

        // Handle changes
        request.onreadystatechange = function() {{
            if(request.readyState == 4) {{
                if(request.status != 200) {{
                    return console.log('[FizzStat]', 'ajax response error: ' + request.status);
                }}

                console.log('[FizzStat]', 'logged event: "' + event_type + '", value: "' + value + '", optional data:', data);
                if(callback) callback();
            }}
        }}

        // Build request
        var json_data = JSON.stringify({{
            'value': value,
            'data': data
        }});

        // Send the request
        request.send(json_data);
    }};

    // If referrer != current host, entry event
    if(document.referrer) {{
        var url = new URL(document.referrer);
        if(url.hostname != window.location.hostname) {{
            event('entry', document.referrer);
        }}
    }}

    // On external link click, exit event
    var links = document.querySelectorAll('a');
    for(var i=0; i<links.length; i++) {{
        var link = links[i];
        link.addEventListener('click', function(e) {{
            var url = new URL(this.href);
            if(url.hostname != window.location.hostname) {{
                // Stop outlinks until we've sent the event
                e.preventDefault();
                event('exit', this.href, null, function() {{ window.location = this.href }}.bind(this));
            }}
        }});
    }}

    // Bind for custom events
    window.fizzstat = {{
        event: event
    }};
}})();
