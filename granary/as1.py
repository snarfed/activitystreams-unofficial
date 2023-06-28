"""Utilities for ActivityStreams 1 objects."""
import collections
import copy
import logging
from operator import itemgetter
import re

from oauth_dropins.webutil import util

logger = logging.getLogger(__name__)

CONTENT_TYPE = 'application/stream+json'

# maps each AS1 RSVP verb to the collection inside an event object that the
# RSVPing actor would go into.
RSVP_VERB_TO_COLLECTION = collections.OrderedDict((  # in priority order
  ('rsvp-yes', 'attending'),
  ('rsvp-no', 'notAttending'),
  ('rsvp-maybe', 'maybeAttending'),
  ('rsvp-interested', 'interested'),
  ('invite', 'invited'),
))
VERBS_WITH_OBJECT = {
  'follow',
  'like',
  'react',
  'share',
} | set(RSVP_VERB_TO_COLLECTION.keys())

# objectTypes that can be actors. technically this is based on AS2 semantics,
# since it's unspecified in AS1.
# https://www.w3.org/TR/activitystreams-core/#actors
# https://activitystrea.ms/specs/json/1.0/#activity
ACTOR_TYPES = {
  'application',
  'group',
  'organization',
  'person',
  'service',
}

# used in original_post_discovery
_PERMASHORTCITATION_RE = re.compile(r'\(([^:\s)]+\.[^\s)]{2,})[ /]([^\s)]+)\)$')


def object_type(obj):
  """Returns the object type, or the verb if it's an activity object.

  Details: http://activitystrea.ms/specs/json/1.0/#activity-object

  Args:
    obj: decoded JSON ActivityStreams object

  Returns:
    string: ActivityStreams object type
  """
  type = obj.get('objectType')
  return type if type and type != 'activity' else obj.get('verb')


def get_object(obj, field='object'):
  """Extracts and returns a field value as an object.

  If the field value is a string, returns an object with it as the id, eg
  {'id': val}. If the field value is a list, returns the first element.

  Args:
    obj: decoded JSON ActivityStreams object
    field: str

  Returns: dict
  """
  if not obj:
    return {}
  val = util.get_first(obj, field, {}) or {}
  return {'id': val} if isinstance(val, str) else val


def get_objects(obj, field='object'):
  """Extracts and returns a field value as an object.

  If the field value is a string, returns an object with it as the id, eg
  {'id': val}. If the field value is a list, returns the first element.

  Args:
    obj: decoded JSON ActivityStreams object
    field: str

  Returns: dict
  """
  if not obj:
    return []
  return [{'id': val} if isinstance(val, str) else val
          for val in util.get_list(obj, field)]


def get_url(obj):
  """Returns the url field's first text value, or None.

  Somewhat duplicates :func:`microformats2.get_text`.
  """
  url = util.get_first(obj, 'url')
  if isinstance(url, dict):
    url = url.get('value')
  return url.strip() if url else ''


def get_ids(obj, field):
  """Extracts and returns a given field's values as ids.

  Args:
    obj: decoded JSON ActivityStreams object
    field: str

  Returns string values as is. For dict values, returns their inner `id` or
  `url` field value, in that order of precedence.
  """
  ids = set()
  for elem in util.get_list(obj, field):
    if elem and isinstance(elem, str):
      ids.add(elem)
    elif isinstance(elem, dict):
      id = elem.get('id') or elem.get('url')
      if id:
        ids.add(id)

  return list(ids)


def merge_by_id(obj, field, new):
  """Merges new items by id into a field in an existing AS1 object.

  Merges new items by id into the given field. If it exists, it must be a list.
  Requires all existing and new items in the field to have ids.

  Args:
    obj: dict, AS1 object
    field: str, name of field to merge new items into
    new: sequence of AS1 dicts
  """
  merged = {o['id']: o for o in obj.get(field, []) + new}
  obj[field] = sorted(merged.values(), key=itemgetter('id'))


def is_public(obj):
  """Returns True if the object is public, False if private, None if unknown.

  ...according to the Audience Targeting extension:
  http://activitystrea.ms/specs/json/targeting/1.0/

  Expects values generated by this library: objectType group, alias @public,
  @unlisted, or @private.

  Also, important point: this defaults to true, ie public. Bridgy depends on
  that and prunes the to field from stored activities in Response objects (in
  bridgy/util.prune_activity()). If the default here ever changes, be sure to
  update Bridgy's code.
  """
  to = obj.get('to') or get_object(obj).get('to') or []
  aliases = util.trim_nulls([t.get('alias') for t in to])
  object_types = util.trim_nulls([t.get('objectType') for t in to])
  return (True if '@public' in aliases or '@unlisted' in aliases
          else None if 'unknown' in object_types
          else False if aliases
          else True)


def add_rsvps_to_event(event, rsvps):
  """Adds RSVP objects to an event's attending fields, in place.

  Args:
    event: ActivityStreams event object
    rsvps: sequence of ActivityStreams RSVP activity objects
  """
  for rsvp in rsvps:
    field = RSVP_VERB_TO_COLLECTION.get(rsvp.get('verb'))
    if field:
      event.setdefault(field, []).append(rsvp.get(
          'object' if field == 'invited' else 'actor'))


def get_rsvps_from_event(event):
  """Returns RSVP objects for an event's attending fields.

  Args:
    event: ActivityStreams event object

  Returns:
    sequence of ActivityStreams RSVP activity objects
  """
  id = event.get('id')
  if not id:
    return []
  parsed = util.parse_tag_uri(id)
  if not parsed:
    return []
  domain, event_id = parsed
  url = event.get('url')
  author = event.get('author')

  rsvps = []
  for verb, field in RSVP_VERB_TO_COLLECTION.items():
    for actor in event.get(field, []):
      rsvp = {'objectType': 'activity',
              'verb': verb,
              'object' if verb == 'invite' else 'actor': actor,
              'url': url,
              }

      if event_id and 'id' in actor:
        _, actor_id = util.parse_tag_uri(actor['id'])
        rsvp['id'] = util.tag_uri(domain, f'{event_id}_rsvp_{actor_id}')
        if url:
          rsvp['url'] = '#'.join((url, actor_id))

      if verb == 'invite' and author:
        rsvp['actor'] = author

      rsvps.append(rsvp)

  return rsvps


def activity_changed(before, after, log=False):
  """Returns whether two activities or objects differ meaningfully.

  Only compares a few fields: object type, verb, content, location, and image.
  Notably does *not* compare author and published/updated timestamps.

  This has been tested on Facebook posts, comments, and event RSVPs (only
  content and rsvp_status change) and Google+ posts and comments (content,
  updated, and etag change). Twitter tweets and Instagram photo captions and
  comments can't be edited.

  Args:
    before, after: dicts, ActivityStreams activities or objects

  Returns:
    boolean
  """
  def changed(b, a, field, label, ignore=None):
    b_val = b.get(field)
    a_val = a.get(field)

    if ignore and isinstance(b_val, dict) and isinstance(a_val, dict):
      b_val = copy.copy(b_val)
      a_val = copy.copy(a_val)
      for field in ignore:
        b_val.pop(field, None)
        a_val.pop(field, None)

    if b_val != a_val and (a_val or b_val):
      if log:
        logger.debug(f'{label}[{field}] {b_val} => {a_val}')
      return True

  obj_b = get_object(before)
  obj_a = get_object(after)
  if any(changed(before, after, field, 'activity') or
         changed(obj_b, obj_a, field, 'activity[object]')
         for field in ('objectType', 'verb', 'to', 'content', 'location',
                       'image')):
    return True

  if (changed(before, after, 'inReplyTo', 'inReplyTo', ignore=('author',)) or
      changed(obj_b, obj_a, 'inReplyTo', 'object.inReplyTo', ignore=('author',))):
    return True

  return False


def append_in_reply_to(before, after):
  """Appends the inReplyTos from the before object to the after object, in place

  Args:
    before, after: dicts, ActivityStreams activities or objects
  """
  obj_b = get_object(before) or before
  obj_a = get_object(after) or after

  if obj_b and obj_a:
    reply_b = util.get_list(obj_b, 'inReplyTo')
    reply_a = util.get_list(obj_a, 'inReplyTo')
    obj_a['inReplyTo'] = util.dedupe_urls(reply_a + reply_b)


def actor_name(actor):
  """Returns the given actor's name if available, otherwise Unknown."""
  if actor:
    return actor.get('displayName') or actor.get('username') or 'Unknown'
  return 'Unknown'


def original_post_discovery(
    activity, domains=None, include_redirect_sources=True,
    include_reserved_hosts=True, max_redirect_fetches=None, **kwargs):
  """Discovers original post links.

  This is a variation on http://indiewebcamp.com/original-post-discovery . It
  differs in that it finds multiple candidate links instead of one, and it
  doesn't bother looking for MF2 (etc) markup because the silos don't let you
  input it. More background:
  https://github.com/snarfed/bridgy/issues/51#issuecomment-136018857

  Original post candidates come from the upstreamDuplicates, attachments, and
  tags fields, as well as links and permashortlinks/permashortcitations in the
  text content.

  Args:
    activity: activity dict
    domains: optional sequence of domains. If provided, only links to these
      domains will be considered original and stored in upstreamDuplicates.
      (Permashortcitations are exempt.)
    include_redirect_sources: boolean, whether to include URLs that redirect
      as well as their final destination URLs
    include_reserved_hosts: boolean, whether to include domains on reserved
      TLDs (eg foo.example) and local hosts (eg http://foo.local/,
      http://my-server/)
    max_redirect_fetches: if specified, only make up to this many HTTP
      fetches to resolve redirects.
    kwargs: passed to requests.head() when following redirects

  Returns:
    ([string original post URLs], [string mention URLs]) tuple
  """
  obj = get_object(activity) or activity
  content = obj.get('content', '').strip()

  # find all candidate URLs
  tags = [t.get('url') for t in obj.get('attachments', []) + obj.get('tags', [])
          if t.get('objectType') in ('article', 'mention', 'note', None)]
  candidates = (tags + util.extract_links(content) +
                obj.get('upstreamDuplicates', []) +
                util.get_list(obj, 'targetUrl'))

  # Permashortcitations (http://indiewebcamp.com/permashortcitation) are short
  # references to canonical copies of a given (usually syndicated) post, of
  # the form (DOMAIN PATH). We consider them an explicit original post link.
  candidates += [match.expand(r'http://\1/\2') for match in
                 _PERMASHORTCITATION_RE.finditer(content)]

  candidates = util.dedupe_urls(
    util.clean_url(url) for url in candidates
    if url and (url.startswith('http://') or url.startswith('https://')) and
    # heuristic: ellipsized URLs are probably incomplete, so omit them.
    not url.endswith('...') and not url.endswith('…'))

  # check for redirect and add their final urls
  if max_redirect_fetches and len(candidates) > max_redirect_fetches:
    logger.warning(f'Found {len(candidates)} original post candidates, only resolving redirects for the first {max_redirect_fetches}')
  redirects = {}  # maps final URL to original URL for redirects
  for url in candidates[:max_redirect_fetches]:
    resolved = util.follow_redirects(url, **kwargs)
    if (resolved.url != url and
        resolved.headers.get('content-type', '').startswith('text/html')):
      redirects[resolved.url] = url

  candidates.extend(redirects.keys())

  # use domains to determine which URLs are original post links vs mentions
  originals = set()
  mentions = set()
  for url in util.dedupe_urls(candidates):
    if url in redirects.values():
      # this is a redirected original URL. postpone and handle it when we hit
      # its final URL so that we know the final domain.
      continue

    domain = util.domain_from_link(url)
    if not domain:
      continue

    if not include_reserved_hosts and (
        ('.' not in domain
         or domain.split('.')[-1] in (util.RESERVED_TLDS | util.LOCAL_TLDS))):
      continue

    which = (originals if not domains or util.domain_or_parent_in(domain, domains)
             else mentions)
    which.add(url)
    redirected_from = redirects.get(url)
    if redirected_from and include_redirect_sources:
      which.add(redirected_from)

  logger.info(f'Original post discovery found original posts {originals}, mentions {mentions}')
  return originals, mentions


def prefix_urls(activity, field, prefix):
  """Adds a prefix to all matching URL fields, eg to inject a caching proxy.

  Generally used with the `image` or `stream` fields. For example:

  ```
  >>> prefix_urls({'actor': {'image': 'http://image'}}, 'image', 'https://proxy/')
  {'actor': {'image': 'https://proxy/http://image'}}
  ```

  Skips any URL fields that already start with the prefix. URLs are *not*
  URL-encoded before adding the prefix. (This is currently used with our
  caching-proxy Cloudflare worker and https://cloudimage.io/ , neither of which
  URL-decodes.)

  Args:
    activity: dict, AS1 activity. Modified in place.
    prefix: string
  """
  a = activity
  for elem in ([a, a.get('object'), a.get('author'), a.get('actor')] +
               a.get('replies', {}).get('items', []) +
               a.get('attachments', []) +
               a.get('tags', [])):
    if elem:
      for obj in util.get_list(elem, field):
        url = obj.get('url')
        if url and not url.startswith(prefix):
          # Note that url isn't URL-encoded here, that's intentional, since
          # cloudimage.io and the caching-proxy Cloudflare worker don't decode.
          obj['url'] = prefix + url
      if elem is not a:
        prefix_urls(elem, field, prefix)


def object_urls(obj):
  """Returns an object's unique URLs, preserving order.
  """
  if isinstance(obj, str):
    return obj

  def value(obj):
    return obj.get('value') if isinstance(obj, dict) else obj

  return util.uniquify(util.trim_nulls(
    [value(obj.get('url'))] + [value(u) for u in obj.get('urls', [])]))
