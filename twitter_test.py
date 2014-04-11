# coding=utf-8
"""Unit tests for twitter.py.
"""

__author__ = ['Ryan Barrett <activitystreams@ryanb.org>']

import copy
import json
import mox
import urllib

import microformats2
import source
import twitter
from oauth_dropins import appengine_config
from oauth_dropins.webutil import testutil
from oauth_dropins.webutil import util


# test data
def tag_uri(name):
  return util.tag_uri('twitter.com', name)

TIMELINE = 'https://api.twitter.com/1.1/statuses/home_timeline.json?include_entities=true&count=0'

USER = {  # Twitter
  'created_at': 'Sat May 01 21:42:43 +0000 2010',
  'description': 'my description',
  'location': 'San Francisco',
  'name': 'Ryan Barrett',
  'profile_image_url': 'http://a0.twimg.com/profile_images/866165047/ryan.jpg',
  'screen_name': 'snarfed_org',
  'id_str': '888',
  'protected': False,
  'url': 'http://t.co/pUWU4S',
  'entities': {'url': {'urls': [{'url': 'http://t.co/pUWU4S',
                                 'expanded_url': 'https://snarfed.org/',
                                 }]}},
  }
ACTOR = {  # ActivityStreams
  'displayName': 'Ryan Barrett',
  'image': {
    'url': 'http://a0.twimg.com/profile_images/866165047/ryan.jpg',
    },
  'id': tag_uri('snarfed_org'),
  'numeric_id': '888',
  'published': '2010-05-01T21:42:43',
  'url': 'https://snarfed.org/',
  'location': {'displayName': 'San Francisco'},
  'username': 'snarfed_org',
  'description': 'my description',
  }
TWEET = {  # Twitter
  'created_at': 'Wed Feb 22 20:26:41 +0000 2012',
  'id_str': '100',
  'id': -1,  # we should always use id_str
  'place': {
    'full_name': 'Carcassonne, Aude',
    'id': '31cb9e7ed29dbe52',
    'name': 'Carcassonne',
    'url': 'http://api.twitter.com/1.1/geo/id/31cb9e7ed29dbe52.json',
    },
  'geo':  {
    'type': 'Point',
    'coordinates':  [32.4004416, -98.9852672],
  },
  'user': USER,
  'entities': {
    'media': [{
        'media_url': 'http://p.twimg.com/picture1',
        'url': 'http://t.co/picture',
        'expanded_url': 'http://the/picture1',
        'display_url': 'http://pic.twitter.com/2',
        'indices': [80, 99],
        }, {
        'media_url': 'http://p.twimg.com/picture2',
        'expanded_url': 'http://the/picture2',
        'display_url': 'http://pic.twitter.com/2',
        }],
    'urls': [{
        'expanded_url': 'http://first/link/',
        'url': 'http://t.co/6J2EgYM',
        'indices': [46, 65],
        'display_url': 'first'
        }, {
        'expanded_url': 'http://instagr.am/p/MuW67/',
        'url': 'http://t.co/X',
        'indices': [66, 79],
        'display_url': 'instagr.am/p/MuW67'
      }],
    'hashtags': [{
        'text': 'tcdisrupt',
        'indices': [32, 42]
      }],
    'user_mentions': [{
        'name': 'Twitter',
        'id_str': '783214',
        'id': -1,  # we should always use id_str
        'indices': [0, 8],
        'screen_name': 'foo'
      },
      {
        'name': 'Picture.ly',
        'id_str': '334715534',
        'id': -1,
        'indices': [15, 28],
        'screen_name': 'foo'
      }],
  },
  'text': '@twitter meets @seepicturely at #tcdisrupt <3 http://t.co/6J2EgYM http://t.co/X http://t.co/picture',
  'source': '<a href="http://choqok.gnufolks.org/" rel="nofollow">Choqok</a>',
  'in_reply_to_screen_name': 'other_user',
  'in_reply_to_status_id': 789,
  }
OBJECT = {  # ActivityStreams
  'objectType': 'note',
  'author': ACTOR,
  'displayName': '@twitter meets @seepicturely at #tcdisrupt <3 first instagr.am/p/MuW67 [picture]',
  'content': '@twitter meets @seepicturely at #tcdisrupt <3 first instagr.am/p/MuW67 [picture]',
  'id': tag_uri('100'),
  'published': '2012-02-22T20:26:41',
  'url': 'http://twitter.com/snarfed_org/status/100',
  'image': {'url': 'http://p.twimg.com/picture1'},
  'location': {
    'displayName': 'Carcassonne, Aude',
    'id': '31cb9e7ed29dbe52',
    'url': 'https://maps.google.com/maps?q=32.4004416,-98.9852672',
    },
  'to':[{'objectType':'group', 'alias':'@public'}],
  'tags': [{
      'objectType': 'image',
      'url': 'http://p.twimg.com/picture1',
      'displayName': '[picture]',
      'startIndex': 71,
      'length': 9,
      }, {
      'objectType': 'image',
      'url': 'http://p.twimg.com/picture2',
      'displayName': '[picture]',
      }, {
      'objectType': 'person',
      'id': tag_uri('foo'),
      'url': 'http://twitter.com/foo',
      'displayName': 'Twitter',
      'startIndex': 0,
      'length': 8,
      }, {
      'objectType': 'person',
      'id': tag_uri('foo'),  # same id as above, shouldn't de-dupe
      'url': 'http://twitter.com/foo',
      'displayName': 'Picture.ly',
      'startIndex': 15,
      'length': 13,
      }, {
      'objectType': 'hashtag',
      'url': 'https://twitter.com/search?q=%23tcdisrupt',
      'startIndex': 32,
      'length': 10,
      }, {
      'objectType': 'article',
      'url': 'http://first/link/',
      'displayName': 'first',
      'startIndex': 46,
      'length': 5,
      }, {
      'objectType': 'article',
      'url': 'http://instagr.am/p/MuW67/',
      'displayName': 'instagr.am/p/MuW67',
      'startIndex': 52,
      'length': 18,
      }],
  'attachments': [{
      'objectType': 'image',
      'image': {'url': u'http://p.twimg.com/picture1'},
      }, {
      'objectType': 'image',
      'image': {'url': u'http://p.twimg.com/picture2'},
      }],
  }
ACTIVITY = {  # ActivityStreams
  'verb': 'post',
  'published': '2012-02-22T20:26:41',
  'id': tag_uri('100'),
  'url': 'http://twitter.com/snarfed_org/status/100',
  'actor': ACTOR,
  'object': OBJECT,
  'title': '@twitter meets @seepicturely at #tcdisrupt <3 first instagr.am/p/MuW67 [picture]',
  'generator': {'displayName': 'Choqok', 'url': 'http://choqok.gnufolks.org/'},
  'context': {
    'inReplyTo' : [{
      'objectType' : 'note',
      'url' : 'http://twitter.com/other_user/status/789',
      'id' : tag_uri('789'),
      }]
    },
  }

# This is the original tweet and reply chain:
# 100 (snarfed_org) -- 200 (alice) -- 400 (snarfed_org) -- 500 (alice)
#                   \_ 300 (bob)
REPLIES_TO_SNARFED = {'statuses': [{  # Twitter
      'id_str': '200',
      'user': {'screen_name': 'alice'},
      'text': 'reply 200',
      'in_reply_to_status_id_str': '100',
      'in_reply_to_screen_name': 'snarfed_org',
      }, {
      'id_str': '300',
      'user': {'screen_name': 'bob'},
      'text': 'reply 300',
      'in_reply_to_status_id_str': '100',
      }, {
      'id_str': '500',
      'user': {'screen_name': 'alice'},
      'text': 'reply 500',
      'in_reply_to_status_id_str': '400',
      }]}
REPLIES_TO_ALICE = {'statuses': [{
      'id_str': '400',
      'user': {'screen_name': 'snarfed_org'},
      'text': 'reply 400',
      'in_reply_to_status_id_str': '200',
      }]}
REPLIES_TO_BOB = {'statuses': []}

REPLY_OBJS = [{  # ActivityStreams
    'objectType': 'note',
    'id': tag_uri('200'),
    'author': {
      'id': 'tag:twitter.com:alice',
      'username': 'alice',
      'url': 'http://twitter.com/alice',
      },
    'displayName': 'reply 200',
    'content': 'reply 200',
    'url': 'http://twitter.com/alice/status/200',
    }, {
    'objectType': 'note',
    'id': tag_uri('300'),
    'author': {
      'id': 'tag:twitter.com:bob',
      'username': 'bob',
      'url': 'http://twitter.com/bob',
      },
    'displayName': 'reply 300',
    'content': 'reply 300',
    'url': 'http://twitter.com/bob/status/300',
    }, {
    'objectType': 'note',
    'id': tag_uri('400'),
    'author': {
      'id': 'tag:twitter.com:snarfed_org',
      'username': 'snarfed_org',
      'url': 'http://twitter.com/snarfed_org',
      },
    'displayName': 'reply 400',
    'content': 'reply 400',
    'url': 'http://twitter.com/snarfed_org/status/400',
    }, {
    'objectType': 'note',
    'id': tag_uri('500'),
    'author': {
      'id': 'tag:twitter.com:alice',
      'username': 'alice',
      'url': 'http://twitter.com/alice',
      },
    'displayName': 'reply 500',
    'content': 'reply 500',
    'url': 'http://twitter.com/alice/status/500',
    }]
ACTIVITY_WITH_REPLIES = copy.deepcopy(ACTIVITY)  # ActivityStreams
ACTIVITY_WITH_REPLIES['object']['replies'] = {
  'totalItems': 4,
  'items': REPLY_OBJS,
  }

RETWEETS = [{  # Twitter
    'created_at': 'Wed Feb 24 20:26:41 +0000 2013',
    'id_str': '123',
    'id': -1,  # we should always use id_str
    'user': {
      'name': 'Alice',
      'profile_image_url': 'http://alice/picture',
      'screen_name': 'alizz',
      },
    'retweeted_status': {
      'id_str': '333',
      'id': -1,
      'user': {'screen_name': 'foo'},
      },
  }, {
    'created_at': 'Wed Feb 26 20:26:41 +0000 2013',
    'id_str': '456',
    'id': -1,
    'user': {
      'name': 'Bob',
      'profile_image_url': 'http://bob/picture',
      'screen_name': 'bobbb',
      },
    'retweeted_status': {
      'id_str': '666',
      'id': -1,
      'user': {'screen_name': 'bar'},
      },
    # we replace the content, so this should be stripped
    'entities': {
      'user_mentions': [{
          'name': 'foo',
          'id_str': '783214',
          'indices': [0, 3],
          'screen_name': 'foo',
          }],
      },
    },
]
TWEET_WITH_RETWEETS = copy.deepcopy(TWEET)
TWEET_WITH_RETWEETS['retweets'] = RETWEETS
SHARES = [{  # ActivityStreams
    'id': tag_uri('123'),
    'url': 'http://twitter.com/alizz/status/123',
    'objectType': 'activity',
    'verb': 'share',
    'object': {'url': 'http://twitter.com/foo/status/333'},
    'author': {
      'id': 'tag:twitter.com:alizz',
      'username': 'alizz',
      'displayName': 'Alice',
      'url': 'http://twitter.com/alizz',
      'image': {'url': 'http://alice/picture'},
      },
    'displayName': 'Alice retweeted this.',
    'content': '<a href="http://twitter.com/alizz/status/123">retweeted this.</a>',
    'published': '2013-02-24T20:26:41',
    }, {
    'id': tag_uri('456'),
    'url': 'http://twitter.com/bobbb/status/456',
    'objectType': 'activity',
    'verb': 'share',
    'object': {'url': 'http://twitter.com/bar/status/666'},
    'author': {
      'id': 'tag:twitter.com:bobbb',
      'username': 'bobbb',
      'displayName': 'Bob',
      'url': 'http://twitter.com/bobbb',
      'image': {'url': 'http://bob/picture'},
      },
    'displayName': 'Bob retweeted this.',
    'content': '<a href="http://twitter.com/bobbb/status/456">retweeted this.</a>',
    'published': '2013-02-26T20:26:41',
    }]
OBJECT_WITH_SHARES = copy.deepcopy(OBJECT)
OBJECT_WITH_SHARES['tags'] += SHARES
ACTIVITY_WITH_SHARES = copy.deepcopy(ACTIVITY)
ACTIVITY_WITH_SHARES['object'] = OBJECT_WITH_SHARES
FAVORITE_EVENT = {  # Twitter
  'event' : 'favorite',
  'created_at' : 'Fri Dec 27 17:25:55 +0000 2013',
  'source': {
    'id_str': '789',
    'screen_name': 'eve',
  },
  'target': USER,
  'target_object' : TWEET,
}
LIKE_FROM_EVENT = {  # ActivityStreams
  'id': tag_uri('100_favorited_by_789'),
  'url': 'http://twitter.com/snarfed_org/status/100',
  'objectType': 'activity',
  'verb': 'like',
  'object': {'url': 'http://twitter.com/snarfed_org/status/100'},
  'author': {
    'id': tag_uri('eve'),
    'numeric_id': '789',
    'username': 'eve',
    'url': 'http://twitter.com/eve',
    },
  'displayName': 'eve favorited this.',
  'content': 'favorited this.',
  'published': '2013-12-27T17:25:55',
  }
FAVORITES_HTML = """  # Twitter, from /i/activity/favorited_popup?id=...
<ol class="activity-popup-users">
    <li class="js-stream-item stream-item stream-item
" data-item-id="353" id="stream-item-user-353" data-item-type="user">
    <!-- snipped <div class="account"... -->
  <div class="content">
        <div class="stream-item-header">
          <a class="account-group js-user-profile-link" href="/ge" >
            <img class="avatar js-action-profile-avatar " src="https://twimg/353" alt="" data-user-id="353"/>
            <strong class="fullname js-action-profile-name">George</strong>
              <span class="username js-action-profile-name">@ge</span></a>
        </div>
      </div>
    </div>
    </li>

  <li class="js-stream-item stream-item stream-item">
    <!-- snipped <div class="account"... -->
  <div class="content">
        <div class="stream-item-header">
          <a class="account-group js-user-profile-link" href="/ge" >
              <span class="username js-action-profile-name">@jo</span></a>
        </div>
      </div>
    </div>
    </li>
</ol>
"""
LIKES_FROM_HTML = [{  # ActivityStreams
  'id': tag_uri('100_favorited_by_353'),
  'url': 'http://twitter.com/snarfed_org/status/100',
  'objectType': 'activity',
  'verb': 'like',
  'object': {'url': 'http://twitter.com/snarfed_org/status/100'},
  'author': {
    'id': tag_uri('ge'),
    'numeric_id': '353',
    'username': 'ge',
    'displayName': 'George',
    'url': 'http://twitter.com/ge',
    'image': {'url': 'https://twimg/353'},
    },
  'displayName': 'George favorited this.',
  'content': 'favorited this.',
  }, {
  'url': 'http://twitter.com/snarfed_org/status/100',
  'objectType': 'activity',
  'verb': 'like',
  'object': {'url': 'http://twitter.com/snarfed_org/status/100'},
  'author': {
    'id': tag_uri('jo'),
    'username': 'jo',
    'url': 'http://twitter.com/jo',
    },
  'displayName': 'jo favorited this.',
  'content': 'favorited this.',
  }
]
OBJECT_WITH_LIKES = copy.deepcopy(OBJECT)
OBJECT_WITH_LIKES['tags'] += LIKES_FROM_HTML
ACTIVITY_WITH_LIKES = copy.deepcopy(ACTIVITY)
ACTIVITY_WITH_LIKES['object'] = OBJECT_WITH_LIKES

ATOM = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xml:lang="en-US"
      xmlns="http://www.w3.org/2005/Atom"
      xmlns:activity="http://activitystrea.ms/spec/1.0/"
      xmlns:georss="http://www.georss.org/georss"
      xmlns:ostatus="http://ostatus.org/schema/1.0"
      xmlns:thr="http://purl.org/syndication/thread/1.0"
      >
<generator uri="https://github.com/snarfed/activitystreams-unofficial" version="0.1">
  activitystreams-unofficial</generator>
<id>http://localhost/</id>
<title>User feed for Ryan Barrett</title>

<subtitle>my description</subtitle>

<logo>http://a0.twimg.com/profile_images/866165047/ryan.jpg</logo>
<updated>2012-02-22T20:26:41</updated>
<author>
 <activity:object-type>http://activitystrea.ms/schema/1.0/person</activity:object-type>
 <uri>https://snarfed.org/</uri>
 <name>Ryan Barrett</name>
</author>

<link href="https://snarfed.org/" rel="alternate" type="text/html" />
<link rel="avatar" href="http://a0.twimg.com/profile_images/866165047/ryan.jpg" />
<link href="%(request_url)s" rel="self" type="application/atom+xml" />
<!-- TODO -->
<!-- <link href="" rel="hub" /> -->
<!-- <link href="" rel="salmon" /> -->
<!-- <link href="" rel="http://salmon-protocol.org/ns/salmon-replies" /> -->
<!-- <link href="" rel="http://salmon-protocol.org/ns/salmon-mention" /> -->

<entry>

<author>
 <activity:object-type>http://activitystrea.ms/schema/1.0/person</activity:object-type>
 <uri>https://snarfed.org/</uri>
 <name>Ryan Barrett</name>
</author>

  <activity:object-type>
    http://activitystrea.ms/schema/1.0/note
  </activity:object-type>
  <id>""" + tag_uri('100') + """</id>
  <title>@twitter meets @seepicturely at #tcdisrupt &lt;3 first instagr.am/p/MuW67 [picture]</title>

  <content type="xhtml">
  <div xmlns="http://www.w3.org/1999/xhtml">

@twitter meets @seepicturely at #tcdisrupt &lt;3 first instagr.am/p/MuW67 [picture]

<p><a href=''>
  <img style='float: left' src='http://p.twimg.com/picture1' /><br />
  </a><br />

</p>
<p></p>

<p><a href=''>
  <img style='float: left' src='http://p.twimg.com/picture2' /><br />
  </a><br />

</p>
<p></p>

  </div>
  </content>

  <link rel="alternate" type="text/html" href="http://twitter.com/snarfed_org/status/100" />
  <link rel="ostatus:conversation" href="http://twitter.com/snarfed_org/status/100" />

    <link rel="ostatus:attention" href="http://p.twimg.com/picture1" />
    <link rel="mentioned" href="http://p.twimg.com/picture1" />

    <link rel="ostatus:attention" href="http://p.twimg.com/picture2" />
    <link rel="mentioned" href="http://p.twimg.com/picture2" />

    <link rel="ostatus:attention" href="http://twitter.com/foo" />
    <link rel="mentioned" href="http://twitter.com/foo" />

    <link rel="ostatus:attention" href="http://twitter.com/foo" />
    <link rel="mentioned" href="http://twitter.com/foo" />

    <link rel="ostatus:attention" href="https://twitter.com/search?q=%%23tcdisrupt" />
    <link rel="mentioned" href="https://twitter.com/search?q=%%23tcdisrupt" />

    <link rel="ostatus:attention" href="http://first/link/" />
    <link rel="mentioned" href="http://first/link/" />

    <link rel="ostatus:attention" href="http://instagr.am/p/MuW67/" />
    <link rel="mentioned" href="http://instagr.am/p/MuW67/" />

  <activity:verb>http://activitystrea.ms/schema/1.0/post</activity:verb>
  <published>2012-02-22T20:26:41</published>
  <updated></updated>

    <thr:in-reply-to ref=\"""" + tag_uri('789') + """\" href="http://twitter.com/other_user/status/789" type="text/html" />

  <!-- <link rel="ostatus:conversation" href="" /> -->
  <!-- http://www.georss.org/simple -->

    <georss:featureName>Carcassonne, Aude</georss:featureName>

  <link rel="self" type="application/atom+xml" href="http://twitter.com/snarfed_org/status/100" />
</entry>

</feed>
"""


class TwitterTest(testutil.HandlerTest):

  def setUp(self):
    super(TwitterTest, self).setUp()
    appengine_config.TWITTER_APP_KEY = 'fake'
    appengine_config.TWITTER_APP_SECRET = 'fake'
    self.orig_max_tweet_length = twitter.MAX_TWEET_LENGTH
    self.orig_tco_length = twitter.TCO_LENGTH
    self.twitter = twitter.Twitter('key', 'secret')

  def tearDown(self):
    twitter.MAX_TWEET_LENGTH = self.orig_max_tweet_length
    twitter.TCO_LENGTH = self.orig_tco_length

  def test_get_actor(self):
    self.expect_urlopen(
      'https://api.twitter.com/1.1/users/lookup.json?screen_name=foo',
      json.dumps(USER))
    self.mox.ReplayAll()
    self.assert_equals(ACTOR, self.twitter.get_actor('foo'))

  def test_get_actor_default(self):
    self.expect_urlopen(
      'https://api.twitter.com/1.1/account/verify_credentials.json',
      json.dumps(USER))
    self.mox.ReplayAll()
    self.assert_equals(ACTOR, self.twitter.get_actor())

  def test_get_activities(self):
    self.expect_urlopen(TIMELINE, json.dumps([TWEET, TWEET]))
    self.mox.ReplayAll()
    self.assert_equals([ACTIVITY, ACTIVITY], self.twitter.get_activities())

  def test_get_activities_start_index_count(self):
    tweet2 = copy.deepcopy(TWEET)
    tweet2['user']['name'] = 'foo'
    activity2 = copy.deepcopy(ACTIVITY)
    activity2['actor']['displayName'] = 'foo'

    self.expect_urlopen(
      'https://api.twitter.com/1.1/statuses/home_timeline.json?'
      'include_entities=true&count=2',
      json.dumps([TWEET, tweet2]))
    self.mox.ReplayAll()

    self.assert_equals([activity2],
                       self.twitter.get_activities(start_index=1, count=1))

  def test_get_activities_activity_id(self):
    self.expect_urlopen(
      'https://api.twitter.com/1.1/statuses/show.json?id=000&include_entities=true',
      json.dumps(TWEET))
    self.mox.ReplayAll()

    # activity id overrides user, group, app id and ignores startIndex and count
    self.assert_equals([ACTIVITY], self.twitter.get_activities(
        user_id='123', group_id='456', app_id='789', activity_id='000',
        start_index=3, count=6))

  def test_get_activities_self(self):
    self.expect_urlopen('https://api.twitter.com/1.1/statuses/user_timeline.json?'
                         'include_entities=true&count=0',
                         '[]')
    self.mox.ReplayAll()

    self.assert_equals([], self.twitter.get_activities(group_id=source.SELF))

  def test_get_activities_fetch_replies(self):
    tweet = copy.deepcopy(TWEET)
    self.expect_urlopen(TIMELINE, json.dumps([tweet]))
    self.expect_urlopen(
      'https://api.twitter.com/1.1/search/tweets.json?q=%40snarfed_org&include_entities=true&result_type=recent&count=100&since_id=567',
      json.dumps(REPLIES_TO_SNARFED))
    self.expect_urlopen(
      'https://api.twitter.com/1.1/search/tweets.json?q=%40alice&include_entities=true&result_type=recent&count=100&since_id=567',
      json.dumps(REPLIES_TO_ALICE))
    self.expect_urlopen(
      'https://api.twitter.com/1.1/search/tweets.json?q=%40bob&include_entities=true&result_type=recent&count=100&since_id=567',
      json.dumps(REPLIES_TO_BOB))
    self.mox.ReplayAll()

    self.assert_equals([ACTIVITY_WITH_REPLIES],
                       self.twitter.get_activities(fetch_replies=True, min_id='567'))

  def test_get_activities_fetch_shares(self):
    tweet = copy.deepcopy(TWEET)
    tweet['retweet_count'] = 1
    self.expect_urlopen(TIMELINE, json.dumps([tweet]))
    self.expect_urlopen(
      'https://api.twitter.com/1.1/statuses/retweets.json?id=100&since_id=567',
      json.dumps(RETWEETS))
    self.mox.ReplayAll()

    self.assert_equals([ACTIVITY_WITH_SHARES],
                       self.twitter.get_activities(fetch_shares=True, min_id='567'))

  def test_get_activities_fetch_shares_no_retweets(self):
    self.expect_urlopen(TIMELINE, json.dumps([TWEET]))
    # we should only ask the API for retweets when retweet_count > 0
    self.mox.ReplayAll()

    self.assert_equals([ACTIVITY], self.twitter.get_activities(fetch_shares=True))

  def test_get_activities_fetch_cache(self):
    RETWEETS = 'https://api.twitter.com/1.1/statuses/retweets.json?id=100'
    FAVORITES = 'https://twitter.com/i/activity/favorited_popup?id=100'

    for count in (1, 2):
      tweet = copy.deepcopy(TWEET)
      tweet['retweet_count'] = tweet['favorite_count'] = count
      self.expect_urlopen(TIMELINE, json.dumps([tweet]))
      self.expect_urlopen(RETWEETS, '[]')
      self.expect_urlopen(FAVORITES, '{}')
      # shouldn't fetch this time because counts haven't changed
      self.expect_urlopen(TIMELINE, json.dumps([tweet]))

    self.mox.ReplayAll()
    cache = testutil.FakeCache()
    for i in range(4):
      self.twitter.get_activities(fetch_shares=True, fetch_likes=True,
                                  cache=cache)

  def test_get_activities_fetch_likes(self):
    tweet = copy.deepcopy(TWEET)
    tweet['favorite_count'] = 1
    self.expect_urlopen(TIMELINE, json.dumps([tweet]))
    self.expect_urlopen('https://twitter.com/i/activity/favorited_popup?id=100',
      json.dumps({'htmlUsers': FAVORITES_HTML}))
    self.mox.ReplayAll()

    self.assert_equals([ACTIVITY_WITH_LIKES],
                       self.twitter.get_activities(fetch_likes=True))

  def test_get_activities_fetch_likes_no_favorites(self):
    self.expect_urlopen(TIMELINE, json.dumps([TWEET]))
    # we should only ask the API for retweets when favorites_count > 0
    self.mox.ReplayAll()

    self.assert_equals([ACTIVITY], self.twitter.get_activities(fetch_likes=True))

  def test_retweet_limit(self):
    tweet = copy.deepcopy(TWEET)
    tweet['retweet_count'] = 1
    self.expect_urlopen(TIMELINE, json.dumps([tweet] * (twitter.RETWEET_LIMIT + 2)))

    for i in range(twitter.RETWEET_LIMIT):
      self.expect_urlopen(
        'https://api.twitter.com/1.1/statuses/retweets.json?id=100&since_id=567',
        json.dumps(RETWEETS))

    self.mox.ReplayAll()
    self.assert_equals(([ACTIVITY_WITH_SHARES] * twitter.RETWEET_LIMIT) +
                       [ACTIVITY, ACTIVITY],
                       self.twitter.get_activities(fetch_shares=True, min_id='567'))

  def test_get_activities_request_etag(self):
    self.expect_urlopen(TIMELINE, '[]', headers={'If-none-match': '"my etag"'})
    self.mox.ReplayAll()
    self.twitter.get_activities_response(etag='"my etag"')

  def test_get_activities_response_etag(self):
    self.expect_urlopen(TIMELINE, '[]', response_headers={'ETag': '"my etag"'})
    self.mox.ReplayAll()
    self.assert_equals('"my etag"', self.twitter.get_activities_response()['etag'])

  def test_get_activities_304_not_modified(self):
    """Requests with matching ETags return 304 Not Modified."""
    self.expect_urlopen(TIMELINE, '[]', status=304)
    self.mox.ReplayAll()
    self.assert_equals([], self.twitter.get_activities_response()['items'])

  def test_get_activities_min_id(self):
    """min_id shouldn't be passed to the initial request, just the derived ones."""
    self.expect_urlopen(TIMELINE, '[]')
    self.mox.ReplayAll()
    self.twitter.get_activities_response(min_id=135)

  def test_get_comment(self):
    self.expect_urlopen(
      'https://api.twitter.com/1.1/statuses/show.json?id=123&include_entities=true',
      json.dumps(TWEET))
    self.mox.ReplayAll()
    self.assert_equals(OBJECT, self.twitter.get_comment('123'))

  def test_get_share(self):
    self.expect_urlopen(
      'https://api.twitter.com/1.1/statuses/show.json?id=123&include_entities=true',
      json.dumps(RETWEETS[0]))
    self.mox.ReplayAll()
    self.assert_equals(SHARES[0], self.twitter.get_share('user', 'tweet', '123'))

  def test_tweet_to_activity_full(self):
    self.assert_equals(ACTIVITY, self.twitter.tweet_to_activity(TWEET))

  def test_tweet_to_activity_minimal(self):
    # just test that we don't crash
    self.twitter.tweet_to_activity({'id': 123, 'text': 'asdf'})

  def test_tweet_to_activity_empty(self):
    # just test that we don't crash
    self.twitter.tweet_to_activity({})

  def test_tweet_to_object_full(self):
    self.assert_equals(OBJECT, self.twitter.tweet_to_object(TWEET))

  def test_tweet_to_object_minimal(self):
    # just test that we don't crash
    self.twitter.tweet_to_object({'id': 123, 'text': 'asdf'})

  def test_tweet_to_object_empty(self):
    self.assert_equals({}, self.twitter.tweet_to_object({}))

  def test_tweet_to_object_with_retweets(self):
    self.assert_equals(OBJECT_WITH_SHARES,
                       self.twitter.tweet_to_object(TWEET_WITH_RETWEETS))

  def test_tweet_to_object_entity_indices_handle_display_urls(self):
    tweet = {
      'id_str': '123',
      'text': '@schnarfed Hey Ryan, You might find this semi-related and interesting: https://t.co/AFGvnvG72L Heard about it from @danshipper this week.',
      'entities': {
        'urls': [{
            'url': 'https://t.co/AFGvnvG72L',
            'expanded_url': 'https://www.onename.io/',
            'display_url': 'onename.io',
            'indices': [71, 94],
            }],
        'user_mentions': [{
            'screen_name': 'danshipper',
            'name': 'Dan Shipper',
            'indices': [115, 126],
            }],
        },
      }

    obj = self.twitter.tweet_to_object(tweet)
    for tag in obj['tags']:
      if tag['displayName'] == 'Dan Shipper':
        self.assertEquals(102, tag['startIndex'])
        self.assertEquals(11, tag['length'])
        break
    else:
      self.fail('Dan Shipper not found')

    self.assertEquals('@schnarfed Hey Ryan, You might find this semi-related and interesting: <a href="https://www.onename.io/">onename.io</a> Heard about it from <a href="http://twitter.com/danshipper">@danshipper</a> this week.',
                      microformats2.render_content(obj))

  def test_protected_tweet_to_object(self):
    tweet = copy.deepcopy(TWEET)
    tweet['user']['protected'] = True
    obj = copy.deepcopy(OBJECT)
    obj['to'][0]['alias'] = '@private'
    self.assert_equals(obj, self.twitter.tweet_to_object(tweet))

  def test_retweet_to_object(self):
    for retweet, share in zip(RETWEETS, SHARES):
      self.assert_equals(share, self.twitter.retweet_to_object(retweet))

    # not a retweet
    self.assertEquals(None, self.twitter.retweet_to_object(TWEET))

  def test_streaming_event_to_object(self):
    self.assert_equals(LIKE_FROM_EVENT,
                       self.twitter.streaming_event_to_object(FAVORITE_EVENT))

    # not a favorite event
    follow = {
      'event': 'follow',
      'source': USER,
      'target': USER,
      'target_object': TWEET,
      }
    self.assertEquals(None, self.twitter.streaming_event_to_object(follow))

  def test_favorites_html_to_likes(self):
    self.assert_equals([], self.twitter.favorites_html_to_likes(TWEET, ""))
    self.assert_equals(LIKES_FROM_HTML,
                       self.twitter.favorites_html_to_likes(TWEET, FAVORITES_HTML))

  def test_user_to_actor_full(self):
    self.assert_equals(ACTOR, self.twitter.user_to_actor(USER))

  def test_user_to_actor_url_fallback(self):
    user = copy.deepcopy(USER)
    del user['url']
    actor = copy.deepcopy(ACTOR)
    actor['url'] = 'http://twitter.com/snarfed_org'
    self.assert_equals(actor, self.twitter.user_to_actor(user))

  def test_user_to_actor_minimal(self):
    # just test that we don't crash
    self.twitter.user_to_actor({'screen_name': 'snarfed_org'})

  def test_user_to_actor_empty(self):
    self.assert_equals({}, self.twitter.user_to_actor({}))

  def test_oauth(self):
    def check_headers(headers):
      sig = dict(headers)['Authorization']
      return (sig.startswith('OAuth ') and
              'oauth_token="key"' in sig and
              'oauth_signature=' in sig)

    self.expect_urlopen(
      'https://api.twitter.com/1.1/users/lookup.json?screen_name=foo',
      json.dumps(USER),
      headers=mox.Func(check_headers))
    self.mox.ReplayAll()

    self.twitter.get_actor('foo')

  def test_create_tweet(self):
    twitter.MAX_TWEET_LENGTH = 20
    twitter.TCO_LENGTH = 5

    dots = u'…'.encode('utf-8')
    original = (
      'my status',
      'too long, will be ellipsized',
      'url shorten http://foo/bar',
      'url http://foo/bar ellipsize http://foo/baz',
      'long url http://www.foo/bar/baz/baj/biff/boof',
      'trailing slash http://www.foo/',
      )
    created = (
      'my status',
      'too long, will be' + dots,
      'url shorten http://foo/bar',
      'url http://foo/bar ellipsize' + dots,
      'long url http://www.foo/bar/baz/baj/biff/boof',
      'trailing slash http://www.foo/',
      )
    previewed = (
      'my status',
      'too long, will be' + dots,
      'url shorten <a href="http://foo/bar">foo/bar</a>',
      'url <a href="http://foo/bar">foo/bar</a> ellipsize' + dots,
      'long url <a href="http://www.foo/bar/baz/baj/biff/boof">foo/bar/baz/baj/bi...</a>',
      'trailing slash <a href="http://www.foo/">foo/</a>',
      )

    for content in created:
      self.expect_urlopen(
        twitter.API_POST_TWEET_URL + '?status=' + urllib.quote_plus(content),
        json.dumps(TWEET), data='')
    self.mox.ReplayAll()

    tweet = copy.deepcopy(TWEET)
    tweet.update({
        'id': '100',
        'url': 'http://twitter.com/snarfed_org/status/100',
        'type': 'post',
        })

    obj = copy.deepcopy(OBJECT)
    for preview, orig in zip(previewed, original):
      obj['content'] = orig
      self.assert_equals(tweet, self.twitter.create(obj))

      got = self.twitter.preview_create(obj)
      self.assertIn('will <span class="verb">tweet</span>', got)
      self.assertIn('<em>%s</em>' % preview, got)

  def test_create_tweet_include_link(self):
    twitter.MAX_TWEET_LENGTH = 20
    twitter.TCO_LENGTH = 5

    self.expect_urlopen(twitter.API_POST_TWEET_URL + '?status=' +
                        urllib.quote_plus('too long… (http://obj)'),
                        json.dumps(TWEET), data='')
    self.mox.ReplayAll()

    obj = copy.deepcopy(OBJECT)
    obj.update({
        'content': 'too long\nextra whitespace\tbut should include url',
        'url': 'http://obj',
        })
    self.twitter.create(obj, include_link=True)
    self.assertIn('too long… (<a href="http://obj">obj</a>)',
                  self.twitter.preview_create(obj, include_link=True))

  def test_create_reply(self):
    # tuples: (content, in-reply-to url, expected tweet, expected type)
    testdata = (
      # good reply, with @-mention of author
      ('foo @you', 'http://twitter.com/you/status/100', 'foo @you', 'comment'),
      # no @-mention of in-reply-to author, so we add it
      ('foo', 'http://twitter.com/you/status/100', '@you foo', 'comment'),
      # photo URL. tests Twitter.base_object()
      ('foo', 'http://twitter.com/you/status/100/photo/1', '@you foo', 'comment'),
      # mobile.twitter.com URL. the mobile should be stripped from embed.
      ('foo', 'http://mobile.twitter.com/you/status/100', '@you foo', 'comment'),
      # reply to different source domain, so we don't treat it as a reply
      ('@you my reply', 'http://other.com', '@you my reply', 'post'),
      )

    for _, _, expected_tweet, type in testdata:
      params = 'status=%s' % urllib.quote_plus(expected_tweet)
      if type == 'comment':
        params += '&in_reply_to_status_id=100'
      self.expect_urlopen(twitter.API_POST_TWEET_URL + '?' + params,
                          json.dumps(TWEET), data='')
    self.mox.ReplayAll()

    tweet = copy.deepcopy(TWEET)
    obj= copy.deepcopy(REPLY_OBJS[0])

    for content, url, expected_tweet, type in testdata:
      tweet.update({
          'id': '100',
          'url': 'http://twitter.com/snarfed_org/status/100',
          'type': type,
          })
      obj.update({'inReplyTo': [{'url': url}],
                  'content': content,
                  })
      self.assert_equals(tweet, self.twitter.create(obj))

      preview = self.twitter.preview_create(obj)
      if type == 'comment':
        self.assertIn(expected_tweet, preview)
        self.assertIn('<span class="verb">@-reply</span>', preview)
        self.assertIn('...to <a href="http://twitter.com/you/status/100', preview)

  def test_create_favorite(self):
    self.expect_urlopen(twitter.API_POST_FAVORITE_URL + '?id=100',
                        json.dumps(TWEET), data='')
    self.mox.ReplayAll()
    self.assert_equals({'url': 'http://twitter.com/snarfed_org/status/100',
                        'type': 'like'},
                       self.twitter.create(LIKES_FROM_HTML[0]))

    preview = self.twitter.preview_create(LIKES_FROM_HTML[0])
    self.assertIn('<span class="verb">favorite</span> <a href="http://twitter.com/snarfed_org/status/100">this tweet</a>', preview)

  def test_create_retweet(self):
    self.expect_urlopen(
      'https://api.twitter.com/1.1/statuses/retweet/333.json?id=333',
      json.dumps(TWEET), data='')
    self.mox.ReplayAll()

    tweet = copy.deepcopy(TWEET)
    tweet.update({
        'id': '100',
        'url': 'http://twitter.com/snarfed_org/status/100',
        'type': 'repost',
        })
    self.assert_equals(tweet, self.twitter.create(SHARES[0]))

    preview = self.twitter.preview_create(SHARES[0])
    self.assertIn('<span class="verb">retweet</span> <a href="http://twitter.com/foo/status/333">this tweet</a>', preview)

  def test_create_unsupported_type(self):
    for fn in self.twitter.create, self.twitter.preview_create:
      self.assertRaises(NotImplementedError, fn,
                        {'objectType': 'activity', 'verb': 'rsvp-yes'})
