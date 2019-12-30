from oauth_dropins.webutil import testutil
from oauth_dropins.webutil import util

from granary.meetup import Meetup

import copy
import json

# test data
def tag_uri(name):
    return util.tag_uri('meetup.com', name)

RSVP_ACTIVITY = {
        'id': tag_uri('145304994_rsvp_11500'),
        'objectType': 'activity',
        'verb': 'rsvp-yes',
        'inReplyTo': 'https://meetup.com/PHPMiNDS-in-Nottingham/events/264008439',
        'actor': {
            'objectType': 'person',
            'displayName': 'Jamie T',
            'id': tag_uri('189380737'),
            'numeric_id': '189380737',
            'url': 'https://www.meetup.com/members/189380737/',
            'image': {'url': 'https://secure.meetupstatic.com/photos/member/6/8/7/5/member_288326741.jpeg'},
            },
        }

class MeetupTest(testutil.TestCase):

    def setUp(self):
        super(MeetupTest, self).setUp()
        self.meetup = Meetup('token-here')

    def test_create_rsvp_yes(self):
        self.expect_urlopen(
                url='https://api.meetup.com/PHPMiNDS-in-Nottingham/events/264008439/rsvps',
                data='response=yes',
                response=200,
                headers={
                    'Authorization': 'Bearer token-here'
                    }
                )
        self.mox.ReplayAll()

        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['verb'] = 'rsvp-yes'
        created = self.meetup.create(rsvp)
        self.assert_equals({'url': 'https://meetup.com/PHPMiNDS-in-Nottingham/events/264008439#rsvp-by-189380737', 'type': 'rsvp'},
                created.content,
                '%s\n%s' % (created.content, rsvp))

    def test_create_rsvp_yes_with_www(self):
        self.expect_urlopen(
                url='https://api.meetup.com/PHPMiNDS-in-Nottingham/events/264008439/rsvps',
                data='response=yes',
                response=200,
                headers={
                    'Authorization': 'Bearer token-here'
                    }
                )
        self.mox.ReplayAll()

        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['inReplyTo'] = 'https://www.meetup.com/PHPMiNDS-in-Nottingham/events/264008439'
        rsvp['verb'] = 'rsvp-yes'
        created = self.meetup.create(rsvp)
        self.assert_equals({'url': 'https://www.meetup.com/PHPMiNDS-in-Nottingham/events/264008439#rsvp-by-189380737', 'type': 'rsvp'},
                created.content,
                '%s\n%s' % (created.content, rsvp))

    def test_preview_create_rsvp_yes(self):
        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['verb'] = 'rsvp-yes'
        preview = self.meetup.preview_create(rsvp)
        self.assertEqual('<span class="verb">RSVP yes</span> to '
                          '<a href="https://meetup.com/PHPMiNDS-in-Nottingham/events/264008439">this event</a>.',
                          preview.description)

    def test__create_rsvp_invalid_preview_parameter(self):
        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['verb'] = 'rsvp-yes'
        result = self.meetup._create(rsvp, preview=None)
        self.assertTrue(result.abort)
        self.assertIn('Invalid Preview parameter, must be True or False', result.error_plain)
        self.assertIn('Invalid Preview parameter, must be True or False', result.error_html)

    def test_create_rsvp_no(self):
        self.expect_urlopen(
                url='https://api.meetup.com/PHPMiNDS-in-Nottingham/events/264008439/rsvps',
                data='response=no',
                response=200,
                headers={
                    'Authorization': 'Bearer token-here'
                    }
                )
        self.mox.ReplayAll()

        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['verb'] = 'rsvp-no'
        created = self.meetup.create(rsvp)

        self.assert_equals({'url': 'https://meetup.com/PHPMiNDS-in-Nottingham/events/264008439#rsvp-by-189380737', 'type': 'rsvp'},
                created.content,
                '%s\n%s' % (created.content, rsvp))

    def test_create_rsvp_handles_url_with_trailing_slash(self):
        self.expect_urlopen(
                url='https://api.meetup.com/PHPMiNDS-in-Nottingham/events/264008439/rsvps',
                data='response=yes',
                response=200,
                headers={
                    'Authorization': 'Bearer token-here'
                    }
                )
        self.mox.ReplayAll()

        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['inReplyTo'] = 'https://meetup.com/PHPMiNDS-in-Nottingham/events/264008439/'
        created = self.meetup.create(rsvp)
        self.assert_equals({'url': 'https://meetup.com/PHPMiNDS-in-Nottingham/events/264008439/#rsvp-by-189380737', 'type': 'rsvp'},
                created.content,
                '%s\n%s' % (created.content, rsvp))

    def test_create_rsvp_does_not_support_rsvp_interested(self):
        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['verb'] = 'rsvp-interested'
        result = self.meetup.create(rsvp)

        self.assertTrue(result.abort)
        self.assertIn('Meetup.com does not support rsvp-interested', result.error_plain)
        self.assertIn('Meetup.com does not support rsvp-interested', result.error_html)

    def test_create_rsvp_does_not_support_rsvp_maybe(self):
        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['verb'] = 'rsvp-maybe'
        result = self.meetup.create(rsvp)

        self.assertTrue(result.abort)
        self.assertIn('Meetup.com does not support rsvp-maybe', result.error_plain)
        self.assertIn('Meetup.com does not support rsvp-maybe', result.error_html)

    def test_create_rsvp_does_not_support_other_verbs(self):
        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['verb'] = 'post'
        result = self.meetup.create(rsvp)

        self.assertTrue(result.abort)
        self.assertIn('Meetup.com syndication does not support post', result.error_plain)
        self.assertIn('Meetup.com syndication does not support post', result.error_html)

    def test_create_rsvp_without_in_reply_to(self):
        rsvp = copy.deepcopy(RSVP_ACTIVITY)
        rsvp['inReplyTo'] = None
        result = self.meetup.create(rsvp)

        self.assertTrue(result.abort)
        self.assertIn('missing an in-reply-to', result.error_plain)
        self.assertIn('missing an in-reply-to', result.error_html)

    def test_create_rsvp_with_invalid_url(self):
        for url in ['https://meetup.com/PHPMiNDS-in-Nottingham/', 'https://meetup.com/PHPMiNDS-in-Nottingham/events', 'https://meetup.com/PHPMiNDS-in-Nottingham/events/', 'https://meetup.com//events/264008439', 'https://www.eventbrite.com/e/indiewebcamp-amsterdam-tickets-68004881431/faked']:
            rsvp = copy.deepcopy(RSVP_ACTIVITY)
            rsvp['inReplyTo'] = url
            result = self.meetup.create(rsvp)

            self.assertTrue(result.abort)
            self.assertIn('Invalid Meetup.com event URL', result.error_plain)
            self.assertIn('Invalid Meetup.com event URL', result.error_html)
