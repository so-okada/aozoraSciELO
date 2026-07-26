#!/usr/bin/env python3
# written by So Okada so.okada@gmail.com
# a part of aozoraSciELO for retrieval of SciELO Preprints records
# by scielo_oai_parser.py
# https://github.com/so-okada/aozoraSciELO/

import time
import traceback
from datetime import timedelta

from aozoraSciELO_variables import *
import scielo_oai_parser as soap


# One harvest of one bot. What paces requests is oai_page_sleep between
# resumptionToken pages, and bot_wait between one bot and the next.
def daily_entries(label, oai_set, now, num_last_days=None):
    # Reaching back over more than today absorbs a missed run and a late
    # datestamp; the post log keeps the wider window from turning into
    # duplicate posts. A command line -n wins over oai_from_days.
    from_days = oai_from_days if num_last_days is None else num_last_days
    from_date = (now - timedelta(days=from_days)).strftime("%Y-%m-%d")

    trial_num = 0
    while trial_num < oai_max_trial:
        try:
            feed = soap.retrieve(label, oai_set, from_date)
            print("harvested " + str(feed.total) + " record(s) in "
                  + str(feed.pages) + " page(s) for " + label
                  + " from " + from_date)
            return feed
        except soap.OAIProtocolError:
            # a rejected request, a bad set, or a bad date range fails
            # identically on every try. Report it and stop.
            print("**harvest request refused for " + label
                  + ", not retrying")
            traceback.print_exc()
            raise
        except Exception:
            print(str(trial_num + 1) + "th harvest error for " + label)
            traceback.print_exc()

        trial_num += 1
        if trial_num < oai_max_trial:
            print("sleep " + str(oai_retry_sleep) + "s and retry for "
                  + label)
            time.sleep(oai_retry_sleep)
        else:
            raise Exception("fatal harvest error for " + label)
