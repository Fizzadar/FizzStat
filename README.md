# FizzStat

Simple web stats without tracking cookies or localstorage equivalents. A quick holiday hack. Elasticsearch as the main storage backend (with a Redis queue inbetween).

+ **collect.py** - tiny Flask server to serve the JS and collect the stats (in most basic form), writing to a Redis queue
+ **import.py** - reads from the Redis queue, does some simple parsing and writes to Elasticsearch


## FizzDash / Viewing the Stats

I threw together a quick dashboard for analyzing the results in Elasticsearch, see [FizzDash]().


## Install

Assumes Redis/Elasticsearch setup locally:

```sh
# Setup Elasticsearch mappings
export ES_HOST=localhost
curl -X PUT  http://$ES_HOST:9200/fizzstat/client/_mapping -d@mappings.clients.json
curl -X PUT  http://$ES_HOST:9200/fizzstat/event/_mapping -d@mappings.events.json
curl -X PUT  http://$ES_HOST:9200/fizzstat/view/_mapping -d@mappings.views.json

# Install Python dependencies
pip install -r requirements.pip
```

Optionally create a file called `settings_ext.py` with your own settings, the defaults are found in `settings.py`. **In production it is recommended to limit the `ALLOWED_HOSTS`**.

Installing the code on a site is pretty simple, in basic form without any clientside generated hash:

```js
// Async load of collect JS w/ cache-bust
window.addEventListener('load', function() {
    var script = document.createElement('script');
    script.src = '//localhost:5000?' + new Date().getTime();
    document.body.appendChild(script);
});
```


## Running Server & Importer

It is recommended to run the server under uwsgi and the importer using a process monitor such as supervisor.


## Tracking Sessions

FizzStat uses some server-side indicators (IP, user agent string, accepted languages/encodings) to generate a client hash. Additional hash data can be sent down by adding a `client_hash` query string parameter to the initial request. Sadly the use of IP's makes tracking mobile user sessions more difficult as they tend to change regularly. The `test.html` file includes an implementation for generating a clientside hash based on the available browser plugins/etc - but one could easily use logged in user ID's or similar. The client hash is also stored under the client in Elasticsearch, so you can use this to track a single user (with a known hash).

When the initial request is made, FizzStat logs the view and assigns it a key, which is passed down in auto-generated JavaScript. This view key is then used to tie events to a view.


## Events

+ `entry` - external referrers
+ `edit` - clicks to external links
+ `<custom>` - anything you like! (`fizzstat.event(<name>, <value>, <optional data>, <optional callback>)`)


## Distributed

One could easily distribute/scale by simply adding lots of collect/import/Redis servers and round-robining them.


## Data Structures

As represented in Elasticsearch:

+ **clients** - a client, defined by IP and browser fingerprint
+ **views** - single page views, reference a client
+ **events** - reference a view (ie external referrers, outlink clicks, etc)
