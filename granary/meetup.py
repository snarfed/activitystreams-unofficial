# coding=utf-8
"""Meetup.com source class.
"""

from . import source
import datetime
import logging
from oauth_dropins import meetup
from oauth_dropins.webutil import util
import re
import urllib.parse, urllib.request

API_BASE = 'https://api.meetup.com'
API_RSVPS = '/%(urlname)s/events/%(event_id)s/rsvps'

# We don't want to be too strict here with what a valid urlname and event_id
# are because Meetup.com haven't documented it too well, and it may change
EVENT_URL_RE = re.compile(r'https://(www\.|)meetup.com/([^/]+)/events/([0-9]+)/?$')

class Meetup(source.Source):

    DOMAIN = 'meetup.com'
    NAME = 'Meetup.com'

    URL_CANONICALIZER = util.UrlCanonicalizer(
            domain=DOMAIN,
            approve=EVENT_URL_RE)

    def __init__(self, access_token):
        self.access_token = access_token
        pass

    def create(self, obj, include_link=source.OMIT_LINK, ignore_formatting=False):
        return self._create(obj, False, include_link, ignore_formatting)

    def preview_create(self, obj, include_link=source.OMIT_LINK, ignore_formatting=False):
        return self._create(obj, True, include_link, ignore_formatting)

    def post_rsvp(self, urlname, event_id, response):
        url = API_BASE + API_RSVPS % {
                'urlname': urlname,
                'event_id': event_id,
                }
        params = 'response=%(response)s' % {
                'response': response,
                }
        logging.debug('Creating RSVP=%(rsvp)s for %(urlname)s %(event_id)s' % {
            'rsvp': response,
            'urlname': urlname,
            'event_id': event_id,
            })
        return meetup.urlopen_bearer_token(url, self.access_token, data=params)

    def _create(self, obj, preview=False, include_link=source.OMIT_LINK, ignore_formatting=False):
        if not preview in (False, True):
            return self.return_error('Invalid Preview parameter, must be True or False')
        verb = obj.get('verb')
        response = None
        if verb == 'rsvp-yes':
            response = 'yes'
        elif verb == 'rsvp-no':
            response = 'no'
        elif verb == 'rsvp-maybe' or verb == 'rsvp-interested':
            return self.return_error('Meetup.com does not support %(verb)s' % {'verb': verb})
        else:
            return self.return_error('Meetup.com syndication does not support %(verb)s' % {'verb': verb})

        # parse the in-reply-to out
        url_containers = obj.get('object')
        if not url_containers:
            return self.return_error('missing an in-reply-to')
        if not 'url' in url_containers[0]:
            return self.return_error('missing an in-reply-to')

        event_url = url_containers[0]['url']
        if not event_url:
            return self.return_error('missing an in-reply-to')

        event_url = self.URL_CANONICALIZER(event_url)
        if not event_url:
            return self.return_error('Invalid Meetup.com event URL')

        parsed_url_part = EVENT_URL_RE.match(event_url)
        if not parsed_url_part:
            return self.return_error('Invalid Meetup.com event URL')

        urlname = parsed_url_part.group(2)
        event_id = parsed_url_part.group(3)

        if preview:
            desc = ('<span class="verb">RSVP %s</span> to <a href="%s">this event</a>.' %
                    (verb[5:], event_url))
            return source.creation_result(description=desc)

        create_resp = {
                'url': '%(event_url)s#rsvp-by-%(url)s' % {
                    'event_url': event_url,
                    'url': urllib.parse.quote_plus(obj['actor']['url']),
                    },
                'type': 'rsvp'
                }

        resp = self.post_rsvp(urlname, event_id, response)
        logging.debug('Response: %s %s', resp.getcode(), resp.read())

        return source.creation_result(create_resp)

    def return_error(self, msg):
        return source.creation_result(abort=True, error_plain=msg, error_html=msg)

    def user_to_actor(self, user):
      """Converts a user to an actor.

      Args:
        user: dict, a decoded JSON Meetup user

      Returns:
        an ActivityStreams actor dict, ready to be JSON-encoded
      """
      user_id = user.get('id')
      user_id_str = str(user_id)
      published_s = round(user.get('joined') / 1000)
      published_dt = datetime.datetime.utcfromtimestamp(published_s)
      return util.trim_nulls({
        'objectType': 'person',
        'displayName': user.get('name'),
        'image': {'url': user.get('photo', {}).get('photo_link')},
        'id': self.tag_uri(user_id_str),
        # numeric_id is our own custom field that always has the source's numeric
        # user id, if available.
        'numeric_id': user_id,
        'published': published_dt.isoformat(),
        'url': self.user_url(user_id_str),
        'urls': None,
        'location': {'displayName': user.get('localized_country_name')},
        'username': user_id_str,
        'description': None,
        })

    def user_url(self, user_id):
      """Returns the URL for a user's profile."""
      return 'https://www.meetup.com/members/%s/' % (user_id)
