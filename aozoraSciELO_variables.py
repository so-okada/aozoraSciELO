# written by So Okada so.okada@gmail.com
# parameters of aozoraSciELO
# https://github.com/so-okada/aozoraSciELO/

# SciELO Preprints OAI-PMH interface
# https://preprints.scielo.org/index.php/scielo/oai
oai_base_url = "https://preprints.scielo.org/index.php/scielo/oai"
oai_metadata_prefix = "oai_dc"
oai_timeout = 60

# user agent string for OAI-PMH requests
oai_user_agent = "aozorascielo-ppbot/1.0 (+https://bsky.app/profile/your_bot)"

# sleep between resumptionToken pages of one harvest
oai_page_sleep = 1
# a safety net against a runaway resumptionToken loop
oai_max_pages = 200

# a ceiling on every request this process sends to the OAI endpoint, bots
# and retries alike.
oai_calls = 1
oai_call_period = 5

# how many times a whole harvest is tried
oai_max_trial = 2
oai_call_sleep = 5 * 60

# a transient server error deserves another try; a malformed request or a
# missing set does not, since it fails the same way every time.
oai_retry_http_codes = (500, 502, 503, 504)
# sleep before retrying a whole harvest.
oai_retry_sleep = 60
# how much of an error page to show.
oai_error_body_len = 800

# how many times to unescape and strip markup out of OJS metadata before
# giving up. Escaping twice happens; a third round is a safety net.
unescape_rounds = 3

# the furthest back a harvest may reach, in days, whether the reach comes
# from -n or from oai_from_days.
oai_from_days_upper_limit = 7

# how many days back a harvest asks for when -n is omitted, counted in
# UTC. Reaching past today absorbs a late datestamp and a missed run,
# and 3 reaches over a weekend for a weekday only schedule. A value
# above oai_from_days_upper_limit stops every run that omits -n.
oai_from_days = 3

# pause between one bot and the next of a multi bot run
bot_wait = 10

# max post length is 300
max_len = 300

# bluesky tags every post with a language, which drives the language
# filters of a feed and the offer to translate. A new submission and its
# abstract carry the language of the preprint. This is for a summary,
# written in English, and for a record whose dc:language says nothing
# usable: the atproto client writes en whenever it is handed nothing, so
# an unknown language becomes this rather than no tag at all.
post_language_default = "en"

# dc:creator of SciELO Preprints carries names in an inverted form such
# as "Silva, Joao da", so a comma cannot separate one author from the
# next. The parser and the formatter must agree on this.
author_separator = "; "

# posts for new submissions:
url_margin = 1
min_len_authors = 60
min_len_title = 120
newsub_spacer = 1
margin = 2

# abstract tag for a counter and a url, as in " [12/34 of <url>]"
# without the url itself, which varies per preprint
abst_tag = 12

# rate limit for each bot
# https://docs.bsky.app/docs/advanced-guides/rate-limits
an_hour = 60 * 60
post_updates = 1500

# limits independent to specific bots
bsky_createaccts_sleep = 3
overall_bsky_limit_call = 2500
overall_bsky_limit_period = 5 * 60
bsky_sleep = 1
