# coding=utf-8
"""Unit tests for mastodon.py."""
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()

import copy

from oauth_dropins.webutil import testutil, util
from oauth_dropins.webutil.util import json_dumps, json_loads

from granary import appengine_config
from granary import as2, mastodon
from granary.mastodon import (
  API_FAVORITE,
  API_MEDIA,
  API_REBLOG,
  API_STATUSES,
)

def tag_uri(name):
  return util.tag_uri('foo.com', name)

INSTANCE = 'http://foo.com'

NOTE = {
  'objectType': 'note',
  'content': 'foo ☕ bar',
}
REPLY = {
  'objectType': 'comment',
  'content': 'reply ☕ baz',
  'inReplyTo': [{'url': 'http://foo.com/@other/123'}],
}
LIKE = {
  'objectType': 'activity',
  'verb': 'like',
  'object': {'url': 'http://foo.com/@snarfed/123'},
}
SHARE = {
  'objectType': 'activity',
  'verb': 'share',
  'object': {'url': 'http://foo.com/@snarfed/123'},
}
NOTE_WITH_MEDIA = {
  'objectType': 'note',
  'content': 'foo ☕ bar',
  'image': [
    {'url': 'http://pic/1'},
    {'url': 'http://pic/2', 'displayName': 'some alt text'},
  ],
  'stream': {'url': 'http://video/3'},
}

NOTE_AS2 = {
  'type': 'Note',
  'content': 'foo ☕ bar',
  'object': {
    'replies': {
      'type': 'Collection',
      'id': 'http://foo.com/123/replies',
    },
  },
}
REPLY_AS2 = {
  'type': 'Note',
  'content': 'reply ☕ baz',
  'inReplyTo': [{'url': 'http://foo.com/@other/123'}],
}

ACCOUNT = {  # Mastodon; https://docs.joinmastodon.org/api/entities/#account
  'id': '23507',
  'username': 'snarfed',
  'acct': 'snarfed',  # fully qualified if on a different instance
  'url': 'http://foo.com/@snarfed',
  'display_name': 'Ryan Barrett',
  'avatar': 'http://foo.com/snarfed.png',
  'created_at': '2017-04-19T20:38:19.704Z',
  'note': 'my note',
  'fields': [{
    'name': 'Web site',
    'value': '<a href="https://snarfed.org" rel="me nofollow noopener" target="_blank"><span class="invisible">https://</span><span class="">snarfed.org</span><span class="invisible"></span></a>',
    'verified_at': '2019-04-03T17:32:24.467+00:00',
  }],
}
ACTOR = {  # ActivityStreams
  'objectType': 'person',
  'displayName': 'Ryan Barrett',
  'username': 'snarfed',
  'id': tag_uri('snarfed'),
  'numeric_id': '23507',
  'url': 'http://foo.com/@snarfed',
  'urls': [
    {'value': 'http://foo.com/@snarfed'},
    {'value': 'https://snarfed.org'},
  ],
  'image': {'url': 'http://foo.com/snarfed.png'},
  'description': 'my note',
  'published': '2017-04-19T20:38:19.704Z',
}
STATUS = {  # Mastodon; https://docs.joinmastodon.org/api/entities/#status
  'id': '123',
  'url': 'http://foo.com/@snarfed/123',
  'uri': 'http://foo.com/users/snarfed/statuses/123',
  'account': ACCOUNT,
  'content': '<p>foo ☕ bar <a ...>@alice</a> <a ...>#IndieWeb</a></p>',
  'created_at': '2019-07-29T18:35:53.446Z',
  'replies_count': 1,
  'favourites_count': 0,
  'reblogs_count': 0,
  'visibility': 'public',
  'mentions': [{
    'username': 'alice',
    'url': 'https://other/@alice',
    'id': '11018',
    'acct': 'alice@other',
  }],
  'tags': [{
    'url': 'http://foo.com/tags/indieweb',
    'name': 'indieweb'
  }],
  'application': {
    'name': 'my app',
    'url': 'http://app',
  },
}
OBJECT = {  # ActivityStreams
  'objectType': 'note',
  'author': ACTOR,
  'content': STATUS['content'],
  'id': tag_uri('123'),
  'published': STATUS['created_at'],
  'url': STATUS['url'],
  'to': [{'objectType': 'group', 'alias': '@public'}],
  'tags': [{
    'objectType': 'mention',
    'id': tag_uri('11018'),
    'url': 'https://other/@alice',
    'displayName': 'alice',
  }, {
    'objectType': 'hashtag',
    'url': 'http://foo.com/tags/indieweb',
    'displayName': 'indieweb',
  }],
}
ACTIVITY = {  # ActivityStreams
  'verb': 'post',
  'published': STATUS['created_at'],
  'id': tag_uri('123'),
  'url': STATUS['url'],
  'actor': ACTOR,
  'object': OBJECT,
  'generator': {'displayName': 'my app', 'url': 'http://app'},
}
REPLY_STATUS = copy.deepcopy(STATUS)  # Mastodon
REPLY_STATUS.update({
  'in_reply_to_id': '456',
  'in_reply_to_account_id': '11018',
})
REPLY_OBJECT = copy.deepcopy(OBJECT)  # ActivityStreams
REPLY_OBJECT['inReplyTo'] = [{
  'url': 'http://foo.com/TODO/status/456',
  'id': tag_uri('456'),
}]
REPLY_ACTIVITY = copy.deepcopy(ACTIVITY)  # ActivityStreams
REPLY_ACTIVITY.update({
  'object': REPLY_OBJECT,
  'context': {'inReplyTo': REPLY_OBJECT['inReplyTo']},
})


class MastodonTest(testutil.TestCase):

  def setUp(self):
    super(MastodonTest, self).setUp()
    self.mastodon = mastodon.Mastodon(INSTANCE, username='alice',
                                      access_token='towkin')

  def expect_api(self, path, response=None, **kwargs):
    kwargs.setdefault('headers', {}).update({
      'Authorization': 'Bearer towkin',
    })
    return self.expect_requests_post(INSTANCE + path, response=response, **kwargs)

  def test_get_activities_defaults(self):
    self.expect_requests_get('http://foo.com/users/alice/outbox?page=true', json_dumps({
      'orderedItems': [
        {'content': 'foo bar'},
        {'content': 'bar baz'},
      ]}), headers=as2.CONNEG_HEADERS)
    self.mox.ReplayAll()

    self.assert_equals([
      {'content': 'foo bar'},
      {'content': 'bar baz'},
    ], self.mastodon.get_activities())

  def test_get_activities_fetch_replies(self):
    self.expect_requests_get('http://foo.com/users/alice/outbox?page=true',
                             json_dumps({'orderedItems': [NOTE_AS2]}),
                             headers=as2.CONNEG_HEADERS)
    self.expect_requests_get('http://foo.com/123/replies?only_other_accounts=true',
                             json_dumps({'items': [REPLY_AS2]}),
                             headers=as2.CONNEG_HEADERS)
    self.mox.ReplayAll()

    expected = copy.deepcopy(NOTE)
    expected['replies'] = {'items': [REPLY]}
    self.assert_equals([expected], self.mastodon.get_activities(fetch_replies=True))

  def test_account_to_actor(self):
    self.assert_equals(ACTOR, self.mastodon.account_to_actor(ACCOUNT))

  def test_status_to_object(self):
    self.assert_equals(OBJECT, self.mastodon.status_to_object(STATUS))

  def test_status_to_activity(self):
    self.assert_equals(ACTIVITY, self.mastodon.status_to_activity(STATUS))

  def test_reply_status_to_object(self):
    self.assert_equals(REPLY_OBJECT, self.mastodon.status_to_object(REPLY_STATUS))

  def test_reply_status_to_activity(self):
    self.assert_equals(REPLY_ACTIVITY, self.mastodon.status_to_activity(REPLY_STATUS))

  def test_preview_status(self):
    got = self.mastodon.preview_create(NOTE)
    self.assertEqual('<span class="verb">toot</span>:', got.description)
    self.assertEqual('foo ☕ bar', got.content)

  def test_create_status(self):
    self.expect_api(API_STATUSES, json={'status': 'foo ☕ bar'}, response=STATUS)
    self.mox.ReplayAll()

    result = self.mastodon.create(NOTE)

    self.assert_equals(STATUS, result.content, result)
    self.assertIsNone(result.error_plain)
    self.assertIsNone(result.error_html)

  def test_create_reply(self):
    self.expect_api(API_STATUSES, json={
      'status': 'reply ☕ baz',
      'in_reply_to_id': '123',
    }, response=STATUS)
    self.mox.ReplayAll()

    result = self.mastodon.create(REPLY)
    self.assert_equals(STATUS, result.content, result)

  def test_create_reply_other_instance(self):
    for fn in (self.mastodon.preview_create, self.mastodon.create):
      got = fn({
        'content': 'foo ☕ bar',
        'inReplyTo': [{'url': 'http://bad/@other/123'}],
      })
      self.assertTrue(got.abort, got)
      self.assertEqual('Could not find a toot on foo.com to reply to.',
                       got.error_plain)

  def test_create_favorite(self):
    self.expect_api(API_FAVORITE % '123', STATUS)
    self.mox.ReplayAll()

    got = self.mastodon.create(LIKE).content
    self.assert_equals('like', got['type'])
    self.assert_equals('http://foo.com/@snarfed/123', got['url'])

  def test_preview_favorite(self):
    preview = self.mastodon.preview_create(LIKE)
    self.assertEqual('<span class="verb">favorite</span> <a href="http://foo.com/@snarfed/123">this toot</a>.', preview.description)

  def test_create_boost(self):
    self.expect_api(API_REBLOG % '123', STATUS)
    self.mox.ReplayAll()

    got = self.mastodon.create(SHARE).content
    self.assert_equals('repost', got['type'])
    self.assert_equals('http://foo.com/@snarfed/123', got['url'])

  def test_preview_boost(self):
    preview = self.mastodon.preview_create(SHARE)
    self.assertEqual('<span class="verb">boost</span> <a href="http://foo.com/@snarfed/123">this toot</a>.', preview.description)

  def test_preview_with_media(self):
    preview = self.mastodon.preview_create(NOTE_WITH_MEDIA)
    self.assertEqual('<span class="verb">toot</span>:', preview.description)
    self.assertEqual('foo ☕ bar<br /><br /><video controls src="http://video/3"><a href="http://video/3">this video</a></video> &nbsp; <img src="http://pic/1" alt="" /> &nbsp; <img src="http://pic/2" alt="some alt text" />',
                     preview.content)

  def test_create_with_media(self):
    self.expect_requests_get('http://pic/1', 'pic 1')
    self.expect_api(API_MEDIA, {'id': 'a'}, files={'file': b'pic 1'})

    self.expect_requests_get('http://pic/2', 'pic 2')
    self.expect_api(API_MEDIA, {'id': 'b'}, files={'file': b'pic 2'})

    self.expect_requests_get('http://video/3', 'vid 3')
    self.expect_api(API_MEDIA, {'id': 'c'}, files={'file': b'vid 3'})

    self.expect_api(API_STATUSES, json={
      'status': 'foo ☕ bar',
      'media_ids': ['a', 'b', 'c'],
    }, response=STATUS)
    self.mox.ReplayAll()

    result = self.mastodon.create(NOTE_WITH_MEDIA)
    self.assert_equals(STATUS, result.content, result)
