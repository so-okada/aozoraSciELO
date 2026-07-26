# Application Info

aozoraSciELO delivers SciELO Preprints daily new submissions, daily
summaries, and abstracts by bluesky posts and replies. aozora means blue
sky (青空/あおぞら) in Japanese. We use python3 scripts with atproto.
aozoraSciELO is not affiliated with SciELO.


## Setup

* Install atproto, pandas, ratelimit, and nameparser.

	```
	% pip3 install atproto pandas ratelimit nameparser
	```

* Let aozoraSciELO.py be executable.

	 ```
	 % chmod +x aozoraSciELO.py
	 ```

*  Put the following python scripts in the same directory.

	- aozoraSciELO.py
	- aozoraSciELO_post.py
	- aozoraSciELO_format.py
	- aozoraSciELO_daily_feed.py
	- scielo_oai_parser.py
	- aozoraSciELO_variables.py


* Configure switches.json and logfiles.json in the tests directory
  for your settings.

	- switches.json specifies bluesky access keys and whether to use
	new submissions, abstracts, and daily summaries by aozoraSciELO.
	Each top level key is a label of one bot.  A bot configured without
	summaries relies on its post log alone to keep a preprint from being
	announced twice, and it makes no post at all on a day with no new
	preprint.

    - logfiles.json indicates log file locations for post summaries,
	posts, and replies.  You can check their formats by
	ppbot_post_summaries.csv, ppbot_posts.csv, and ppbot_replies.csv in
	the tests/logfiles directory.  **aozoraSciELO needs a post log
	file.**  A post log is what keeps a revised preprint from being
	announced a second time, and it keeps the daily summary from being
	posted twice a day.

* Configure aozoraSciELO_variables.py for your settings.

   - aozoraSciELO_variables.py assigns format parameters for
   aozoraSciELO posts and access frequencies for SciELO Preprints and
   bluesky.

## Notes

* scielo_oai_parser.py is a simple OAI-PMH harvester of SciELO
  Preprints for aozoraSciELO. We use this via
  aozoraSciELO_daily_feed.py to regularly obtain data. It asks the
  endpoint for `ListRecords` in `oai_dc`, starting from `oai_from_days`
  days ago in UTC up to the current moment.

* **SciELO Preprints repeats its dc fields once per interface
  language.** A paper by two authors arrives with six `dc:creator`
  elements, tagged `en`, `es` and `pt-BR`, and `dc:title`,
  `dc:subject` and `dc:description` come in the same shape. Taking
  every value would post an author list three times over, so
  aozoraSciELO keeps the values whose `xml:lang` matches `dc:language`,
  falls back on the first language group when nothing matches, and
  drops repeats within the group it chose.

* **A harvest by datestamp mixes new preprints with revised ones.**
  SciELO Preprints stamps a record when it is posted and again whenever
  it is updated, and a revised preprint keeps its identifier.  So a
  datestamp alone cannot say whether a record is new.  aozoraSciELO
  therefore announces a preprint only when its identifier is absent from
  the post log.  Two consequences follow.

	- Without a post log, aozoraSciELO cannot tell a revision from a new
	preprint, and it will announce revised preprints again.  Run it with
	logfiles.json.

	- If the post log cannot be read, aozoraSciELO posts nothing for
	that label rather than risk a second announcement.

* A harvest reaches `-n` days back, and `oai_from_days` days when `-n`
  is omitted. A Monday run reaches back over the weekend with `-n 3`.

* Outputs of aozoraSciELO can differ from the SciELO Preprints web
  pages. This can be due to bugs in my scripts, connection errors, or a
  delay between a preprint appearing on the site and its record reaching
  the OAI interface.

* A daily summary is posted once per UTC day per bot. When a harvest
  fails outright and no summary has gone out yet that day, aozoraSciELO
  still posts a summary reporting no new preprints, so that a silent
  failure does not look like a quiet day. A bot with `summaries` of 0
  reports neither, and a failed harvest leaves only a traceback on
  stdout.

* On the use of metadata of SciELO Preprints, its entry in the COAR
   [Directory of Open Access Preprint Repositories](https://doapr.coar-repositories.org/repositories/scielo-preprints/)
   says "Permission for Re-use of Metadata: CC-0" and "Metadata
   Properties: Title, Identifier, Publication/deposition date, Author
   name(s), Abstract, Relational link to final journal publication (e.g.
   in crossref metadata), License type(s)".  (SciELO's
   [Priority lines of action 2024-2028](https://old-wp.scielo.org/wp-content/uploads/priority-lines-action-2024-2028.pdf)
   says "The metadata of the SciELO Network communication objects have a
   public access license identified by the CC0 code".)


## Usage

```
% ./aozoraSciELO.py -h
usage: aozoraSciELO.py [-h] --switches_keys SWITCHES_KEYS
                       [--logfiles LOGFILES] [--num_last_days NUM_LAST_DAYS]
                       [--mode {0,1}]

SciELO Preprints daily new submissions by posts, daily
summaries by posts, and abstracts by replies.

options:
  -h, --help            show this help message and exit
  --switches_keys SWITCHES_KEYS, -s SWITCHES_KEYS
                        output switches and api keys in
                        json
  --logfiles LOGFILES, -l LOGFILES
                        log file names in json
  --num_last_days NUM_LAST_DAYS, -n NUM_LAST_DAYS
                        how many last days to fetch, 0
                        for today alone,
                        oai_from_days_upper_limit at
                        most. oai_from_days of
                        aozoraSciELO_variables.py when
                        omitted
  --mode {0,1}, -m {0,1}
                        1 for bsky and 0 for stdout
                        only
```


## Sample stdouts

* A dry run of new submissions, a daily summary, and abstracts:

	```
	% ./aozoraSciELO.py -s tests/switches.json -l tests/logfiles.json -m 0
	**process started at xxxx-xx-xx xx:xx:xx (UTC)
	starting retrieval/new submissions/abstracts for SciELO Preprints
	getting daily entries for SciELO Preprints
	OAI request: https://preprints.scielo.org/index.php/scielo/oai?verb=ListRecords&metadataPrefix=oai_dc&from=xxxx-xx-xx
	harvested 2 record(s) in 1 page(s) for SciELO Preprints from xxxx-xx-xx
	new submissions for SciELO Preprints

	utc: xxxx-xx-xx xx:xx:xx
	label: SciELO Preprints
	preprint id:
	root url:
	post method: post
	post mode: 0
	url:
	text: [xxxx-xx-xx Sat (UTC), 2 new preprints found for SciELO Preprints]

	utc: xxxx-xx-xx xx:xx:xx
	label: SciELO Preprints
	preprint id: xxxxx
	root url:
	post method: post
	post mode: 0
	url:
	text: Silva; Souza Ferreira; Oliveira: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx https://preprints.scielo.org/index.php/scielo/preprint/view/xxxxx

	utc: xxxx-xx-xx xx:xx:xx
	label: SciELO Preprints
	preprint id: xxxxx
	root url:
	post method: reply
	post mode: 0
	url:
	text: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx [1/2 of https://preprints.scielo.org/index.php/scielo/preprint/view/xxxxx]

	....

	**process ended at xxxx-xx-xx xx:xx:xx (UTC)
	**elapsed time from the start: xx:xx:xx
	```

* A record already in the post log is not announced again:

	```
	harvested 2 record(s) in 1 page(s) for SciELO Preprints from xxxx-xx-xx
	new submissions for SciELO Preprints
	skipping 1 already announced record(s) for SciELO Preprints
	...
	text: [xxxx-xx-xx Sat (UTC), 1 new preprint found for SciELO Preprints]
	```

* A summary already posted today stops the run:

	```
	new submissions for SciELO Preprints
	SciELO Preprints already posted for today
	```


## Versions

* 0.0.1, initial release.


## Bot List

* [https://bsky.app/profile/aozorascielo-ppbot.bsky.social](https://bsky.app/profile/aozorascielo-ppbot.bsky.social):
  SciELO Preprints — announcement bot (unofficial)


## Author
So Okada, so.okada@gmail.com, https://so-okada.github.io/

## Motivation
This is an open-science practice
(see https://github.com/so-okada/twXiv#motivation).  Since 2013-04, the
author has been running twitter bots for all arXiv math categories.
Since 2023-01, the author has been running mastodon bots for
all arXiv categories with [toXiv](https://github.com/so-okada/toXiv).
Since 2025-02, the author has been running bluesky bots for arXiv
categories with [bXiv](https://github.com/so-okada/bXiv).
Since 2026-07, aozoraSciELO extends the practice to
[SciELO Preprints](https://preprints.scielo.org/) with 
[aozoraSciELO](https://github.com/so-okada/aozoraSciELO).
[SciELO](https://www.scielo.org/en/about-scielo/) is an international
cooperation program for open access scientific communication of all
areas of knowledge, implemented as a public policy and adopted across
Latin America, the Caribbean, Spain, Portugal, and South Africa.

## License
The scripts of aozoraSciELO are under
[AGPLv3](https://www.gnu.org/licenses/agpl-3.0.en.html).
