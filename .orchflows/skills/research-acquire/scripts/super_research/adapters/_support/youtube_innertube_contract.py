"""Stable route contract for the YouTube InnerTube adapter."""

from ... import schema, transport
from .. import AdapterDescriptor, VolatileIdentifier


CLIENT_NAME = "WEB"
CLIENT_VERSION = "2.20260808.00.00"

# The client the transcript operation's player read presents, and the only
# read that presents it. Measured 2026-08-17: `ANDROID` at this version
# answers playability `OK` with a populated caption track list, keyless,
# where `WEB` is served none. Measured 2026-08-31: that same answer carries
# no `microformat` — a whole-body scan found no date field anywhere in it,
# on `IOS` and `ANDROID_VR` alike — while `WEB` still carries `publishDate`
# beside a complete `videoDetails`. So the `player` metadata operation
# presents the web client above, and this one exists for the caption listing
# alone.
PLAYER_CLIENT_NAME = "ANDROID"
PLAYER_CLIENT_VERSION = "20.10.38"

PLAYER_CLIENT_VERSION_RECOVERY = (
    "Rotates with the Android app's own releases. Recover a current one by"
    " hand from a published client table — yt-dlp's `_INNERTUBE_CLIENTS` and"
    " youtube-transcript-api both pin this client and this field — and replace"
    " PLAYER_CLIENT_VERSION here. This package fetches neither: recovery is a"
    " deliberate manual step, because a self-updating identifier would make a"
    " run's own provenance depend on an unrecorded read. A version the origin"
    " refuses answers 400, which is typed stale_identifier, and a version it"
    " serves without captions answers 200 with an empty track list."
)
CLIENT_VERSION_RECOVERY = (
    "Rotates with each YouTube web release. Recover a current one by hand:"
    " fetch youtube.com's own page source and read INNERTUBE_CLIENT_VERSION"
    " out of the ytcfg blob it embeds — the same blob that carries the web"
    " key — and replace CLIENT_VERSION here. This package never fetches that"
    " page: recovery is a deliberate manual step, because a self-updating"
    " identifier would make a run's own provenance depend on an unrecorded"
    " read. A version the origin refuses answers 400 rather than an empty"
    " result set, which is why a refused request is typed stale_identifier."
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="youtube_innertube",
    adapter_version="1",
    access_class="K1",
    route_id=transport.YOUTUBE_INNERTUBE_ROUTE,
    platform="youtube",
    native_identity_namespace="youtube",
    representation_kind="native",
    operator_identity="youtube",
    min_interval_ms=1400,
    volatile_identifiers=(
        VolatileIdentifier(
            name="InnerTube {0} client version {1}".format(CLIENT_NAME, CLIENT_VERSION),
            recovery=CLIENT_VERSION_RECOVERY,
        ),
        VolatileIdentifier(
            name="InnerTube {0} client version {1}".format(
                PLAYER_CLIENT_NAME, PLAYER_CLIENT_VERSION
            ),
            recovery=PLAYER_CLIENT_VERSION_RECOVERY,
        ),
    ),
    reply_count_metric="replyCount",
)
TRANSCRIPT_DESCRIPTOR = AdapterDescriptor(
    adapter_id="youtube_innertube",
    adapter_version="1",
    access_class="K1",
    route_id=transport.YOUTUBE_TIMEDTEXT_ROUTE,
    platform="youtube",
    native_identity_namespace="youtube",
    representation_kind="transcript",
    operator_identity="youtube",
    min_interval_ms=1400,
    page_size=1,
)
SURFACE_DESCRIPTORS = (DESCRIPTOR, TRANSCRIPT_DESCRIPTOR)

NATIVE_ORDER = "youtube_innertube_route_order"
TRANSCRIPT_NATIVE_ORDER = "youtube_timedtext_cue_order"
VIDEO_KIND = "video"
COMMENT_KIND = "comment"
TRANSCRIPT_KIND = "transcript"

SEARCH_OPERATION = "search"
NEXT_OPERATION = "next"
PLAYER_OPERATION = "player"
TRANSCRIPT_OPERATION = "transcript"
INNERTUBE_OPERATIONS = (
    SEARCH_OPERATION,
    NEXT_OPERATION,
    PLAYER_OPERATION,
    TRANSCRIPT_OPERATION,
)

SEARCH_RESULTS_PATH = (
    "contents",
    "twoColumnSearchResultsRenderer",
    "primaryContents",
    "sectionListRenderer",
    "contents",
)
WATCH_NEXT_PATH = (
    "contents",
    "twoColumnWatchNextResults",
    "results",
    "results",
    "contents",
)
RECEIVED_ENDPOINTS_KEY = "onResponseReceivedEndpoints"
RECEIVED_COMMANDS_KEY = "onResponseReceivedCommands"
CONTINUATION_ACTIONS = (
    "appendContinuationItemsAction",
    "reloadContinuationItemsCommand",
)
CONTINUATION_ITEMS_KEY = "continuationItems"
CONTINUATION_ITEM_KEY = "continuationItemRenderer"
CONTINUATION_TOKEN_PATH = (
    "continuationEndpoint",
    "continuationCommand",
    "token",
)
ITEM_SECTION_KEY = "itemSectionRenderer"
SECTION_IDENTIFIER_KEY = "sectionIdentifier"
COMMENT_SECTION_IDENTIFIER = "comment-item-section"
CONTENTS_KEY = "contents"
VIDEO_RENDERER_KEY = "videoRenderer"
COMMENT_THREAD_KEY = "commentThreadRenderer"
COMMENT_PATH = ("comment", "commentRenderer")

COMMENT_VIEW_MODEL_PATH = ("commentViewModel", "commentViewModel")
COMMENT_KEY_FIELD = "commentKey"
ENTITY_MUTATIONS_PATH = ("frameworkUpdates", "entityBatchUpdate", "mutations")
ENTITY_KEY_FIELD = "entityKey"
ENTITY_PAYLOAD_KEY = "payload"
COMMENT_ENTITY_KEY = "commentEntityPayload"
ENTITY_AUTHOR_KEY = "author"
ENTITY_AUTHOR_NAME_KEY = "displayName"
ENTITY_PROPERTIES_KEY = "properties"
ENTITY_CONTENT_KEY = "content"
ENTITY_CONTENT_PATH = (ENTITY_CONTENT_KEY, ENTITY_CONTENT_KEY)
ENTITY_TOOLBAR_KEY = "toolbar"
PUBLISHED_TIME_KEY = "publishedTime"
LIKE_COUNT_NOTLIKED_KEY = "likeCountNotliked"
COMMENT_ENTITY_TEXT_FACTS = (LIKE_COUNT_NOTLIKED_KEY, PUBLISHED_TIME_KEY)

PLAYABILITY_KEY = "playabilityStatus"
PLAYABILITY_STATUS_KEY = "status"
PLAYABILITY_REASON_KEY = "reason"
PLAYABLE_STATUS = "OK"
VIDEO_DETAILS_KEY = "videoDetails"
MICROFORMAT_PATH = ("microformat", "playerMicroformatRenderer")
PUBLISH_DATE_KEY = "publishDate"
EMBED_URL_PATH = ("embed", "iframeUrl")
ATTESTED_PLAYABILITY = ("UNPLAYABLE", "ERROR")
CREDENTIAL_PLAYABILITY = ("LOGIN_REQUIRED", "AGE_VERIFICATION_REQUIRED")

CAPTION_TRACKS_PATH = (
    "captions",
    "playerCaptionsTracklistRenderer",
    "captionTracks",
)
CAPTION_LANGUAGE_FIELD = "languageCode"
CAPTION_KIND_FIELD = "kind"
CAPTION_ASR_KIND = "asr"

TIMEDTEXT_FORMAT_PARAM = "fmt"
TIMEDTEXT_FORMAT = "json3"
TIMEDTEXT_EVENTS_KEY = "events"
TIMEDTEXT_SEGMENTS_KEY = "segs"
TIMEDTEXT_TEXT_KEY = "utf8"
TIMEDTEXT_START_KEY = "tStartMs"
TIMEDTEXT_DURATION_KEY = "dDurationMs"

VIDEO_ID_KEY = "videoId"
TITLE_KEY = "title"
OWNER_TEXT_KEY = "ownerText"
AUTHOR_KEY = "author"
DESCRIPTION_KEY = "shortDescription"
COMMENT_ID_KEY = "commentId"
AUTHOR_TEXT_KEY = "authorText"
CONTENT_TEXT_KEY = "contentText"
NAVIGATION_URL_PATH = (
    "navigationEndpoint",
    "commandMetadata",
    "webCommandMetadata",
    "url",
)
RUNS_KEY = "runs"
SIMPLE_TEXT_KEY = "simpleText"
TEXT_KEY = "text"

VIEW_COUNT_METRIC = "viewCount"
REPLY_COUNT_METRIC = "replyCount"
VIEW_COUNT_TEXT_KEY = "viewCountText"
PUBLISHED_TIME_TEXT_KEY = "publishedTimeText"
VOTE_COUNT_TEXT_KEY = "voteCount"
SEARCH_TEXT_FACTS = (VIEW_COUNT_TEXT_KEY, PUBLISHED_TIME_TEXT_KEY)
COMMENT_TEXT_FACTS = (VOTE_COUNT_TEXT_KEY, PUBLISHED_TIME_TEXT_KEY)

SEARCH_ROW_KEYS = (TITLE_KEY, OWNER_TEXT_KEY)
PLAYER_ROW_KEYS = (TITLE_KEY, VIEW_COUNT_METRIC, PUBLISH_DATE_KEY)
COMMENT_ROW_KEYS = (COMMENT_ID_KEY, CONTENT_TEXT_KEY, AUTHOR_TEXT_KEY)
COMMENT_ENTITY_ROW_KEYS = (
    COMMENT_ID_KEY,
    ENTITY_CONTENT_KEY,
    ENTITY_AUTHOR_NAME_KEY,
)

ROUTE_DATE_FORMAT = "%Y-%m-%d"
ROUTE_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT
DATE_PRECISION_ONLY = "date_precision_only"

STALE_IDENTIFIER_STATUS = 400
AUTHORIZATION_STATUSES = (401, 403)
STALE_IDENTIFIER = "stale_identifier"
ATTESTATION_REQUIRED = "attestation_required"
AUTH_REQUIRED = "auth_required"
WITHHELD = "withheld"
HTTP_STATUS = "http_status"
MALFORMED_JSON = "malformed_json"
SCHEMA_DRIFT = "schema_drift"

CURSOR_VIDEO_FIELD = "sr_video"
CURSOR_LANGUAGE_FIELD = "sr_lang"
CURSOR_KIND_FIELD = "sr_kind"
