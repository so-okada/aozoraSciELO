#!/usr/bin/env python3
# written by So Okada so.okada@gmail.com
# a part of aozoraSciELO for posting to bsky and stdout
# https://github.com/so-okada/aozoraSciELO/

import re
import os
import time
import traceback
from atproto import Client
import pandas as pd
from datetime import datetime, timezone
from ratelimit import limits, sleep_and_retry, rate_limited

from aozoraSciELO_variables import *
import aozoraSciELO_format as aSf
import aozoraSciELO_daily_feed as aSd


def main(switches, logfiles, pt_mode, num_last_days=None):
    starting_time = utcnow()
    print("**process started at " + str(starting_time) + " (UTC)")

    client_dict = {}
    update_dict = {}
    set_dict = {}

    newsubmission_mode = {}
    abstract_mode = {}
    summary_mode = {}

    for cat in switches:
        # stdout mode never reaches bsky, so it needs no login.
        client_dict[cat] = atproto_client(switches[cat]) if pt_mode else None
        update_dict[cat] = sleep_and_retry(
            rate_limited(post_updates, an_hour)(update))
        newsubmission_mode[cat] = int(switches[cat]["newsubmissions"])
        abstract_mode[cat] = int(switches[cat]["abstracts"])
        # a bot that says nothing about a summary still gets one.
        summary_mode[cat] = int(switches[cat].get("summaries", 1))
        # an empty set harvests every SciELO preprint.
        set_dict[cat] = switches[cat].get("set", "")

    # retrieval/new submissions/abstracts, one bot after another. A
    # single OAI endpoint and a per-bot rate limit leave nothing for
    # concurrency to win, and a sequential run keeps a traceback and a
    # keyboard interrupt attached to the bot that caused them.
    for i, cat in enumerate(switches):
        print("starting retrieval/new submissions/abstracts for " + cat)
        newentries(
            logfiles,
            cat,
            set_dict[cat],
            client_dict[cat],
            update_dict[cat],
            newsubmission_mode[cat],
            abstract_mode[cat],
            summary_mode[cat],
            pt_mode,
            num_last_days,
        )
        if i != len(switches) - 1:
            print("waiting before the next bot")
            time.sleep(bot_wait)

    if not logfiles:
        ptext = (
            "No logfiles found. "
            + "aozoraSciELO needs logfiles to keep a preprint from being "
            + "announced twice, since SciELO Preprints restamps a record "
            + "whenever it is updated."
        )
        print(ptext)

    ending_time = utcnow()
    ptext = (
        "\n**process ended at "
        + str(ending_time)
        + " (UTC)"
        + "\n**elapsed time from the start: "
        + str(ending_time - starting_time)
    )
    print(ptext)


class dry_run_result:
    uri = ""
    cid = ""


# post/reply with overall limit
@sleep_and_retry
@limits(calls=overall_bsky_limit_call, period=overall_bsky_limit_period)
def update(
    logfiles,
    cat,
    client,
    total,
    preprint_id,
    text,
    root_uri,
    root_cid,
    parent_uri,
    parent_cid,
    pt_method,
    pt_mode,
    langs,
):
    result = 0

    if not pt_mode:
        update_print(
            cat,
            preprint_id,
            text,
            "",
            "",
            root_uri,
            root_cid,
            parent_uri,
            parent_cid,
            pt_method,
            pt_mode,
            langs,
        )
        # a stand in for a bsky response, so that stdout mode previews a
        # whole thread, abstract replies included.
        return dry_run_result()

    if not client:
        update_print(
            cat,
            preprint_id,
            "\n**error: client not available:\n\n" + text,
            "",
            "",
            root_uri,
            root_cid,
            parent_uri,
            parent_cid,
            pt_method,
            pt_mode,
            langs,
        )
        return result

    error_text = (
        "\nlabel: "
        + cat
        + "\nclient_handle: "
        + client.me.handle
        + "\nclient_did: "
        + client.me.did
        + "\npreprint id: "
        + preprint_id
        + "\ntext: "
        + text
        + "\npt_method: "
        + pt_method
        + "\n"
    )

    if pt_method == "post":
        try:
            result = client.send_post(
                text=text, facets=generate_facets_for_urls(text),
                langs=langs)
            update_print(
                cat,
                preprint_id,
                text,
                result.uri,
                result.cid,
                root_uri,
                root_cid,
                parent_uri,
                parent_cid,
                pt_method,
                pt_mode,
                langs,
            )
        except Exception:
            time_now = utcnow()
            error_text = ("\n**error to post**" + "\nutc: " + str(time_now)
                          + error_text)
            print(error_text)
            traceback.print_exc()
    elif pt_method == "reply":
        try:
            reply_ref = {
                "root": {"uri": root_uri, "cid": root_cid},
                "parent": {"uri": parent_uri, "cid": parent_cid},
            }
            result = client.send_post(
                text=text, reply_to=reply_ref,
                facets=generate_facets_for_urls(text),
                langs=langs
            )
            update_print(
                cat,
                preprint_id,
                text,
                result.uri,
                result.cid,
                root_uri,
                root_cid,
                parent_uri,
                parent_cid,
                pt_method,
                pt_mode,
                langs,
            )
        except Exception:
            time_now = utcnow()
            error_text = ("\n**error to reply**" + "\nutc: " + str(time_now)
                          + error_text)
            print(error_text)
            traceback.print_exc()

    update_log(logfiles, cat, total, preprint_id, result, pt_method, pt_mode)
    time.sleep(bsky_sleep)
    return result


# update stdout text format
def update_print(
    cat,
    preprint_id,
    text,
    result_uri,
    result_cid,
    root_uri,
    root_cid,
    parent_uri,
    parent_cid,
    pt_method,
    pt_mode,
    langs,
):
    time_now = utcnow()
    ptext = (
        "\nutc: "
        + str(time_now)
        + "\nlabel: "
        + cat
        + "\npreprint id: "
        + preprint_id
        + "\nroot url:"
        + atproto_uri_to_url(root_uri)
        + "\npost method: "
        + pt_method
        + "\npost mode: "
        + str(pt_mode)
        + "\nlangs: "
        + ", ".join(langs)
        + "\nurl: "
        + atproto_uri_to_url(result_uri)
        + "\ntext: "
        + text
        + "\n"
    )
    print(ptext)


# The log file entry of one label. switches.json and logfiles.json are
# joined by the label alone, so a label carried by one and not by the
# other is a mistake across a pair of files, and the mistake of one label
# out of many. It must not stop the labels that are configured as they
# should be, so this names the gap and leaves each caller its own safe
# course.
def log_entry(logfiles, cat, keys):
    if not logfiles:
        return None
    if cat not in logfiles:
        print("no log file entry for " + cat + " in logfiles.json")
        return None
    entry = logfiles[cat]
    missing = [one for one in keys if one not in entry]
    if missing:
        print("no " + ", ".join(missing) + " for " + cat
              + " in logfiles.json")
        return None
    return entry


# logging for update
def update_log(logfiles, cat, total, preprint_id, result, pt_method, pt_mode):
    if not result or not pt_mode or not logfiles:
        return None

    time_now = utcnow()
    logname = ("post_summary_log"
               if not preprint_id and pt_method == "post"
               else pt_method + "_log")
    entry = log_entry(logfiles, cat, [logname, "username"])
    if entry is None:
        # what goes unlogged can be posted again: a preprint announced a
        # second time, or a second summary of a day. That is worth a word
        # of its own rather than a silent return.
        print("**not logged for " + cat + ": " + logname
              + (", preprint id: " + preprint_id if preprint_id else ""))
        return None

    if logname == "post_summary_log":
        log_text = [
            [time_now, total, entry["username"], result.uri, result.cid]
        ]
        df = pd.DataFrame(
            log_text, columns=["utc", "total", "username", "uri", "cid"])
    else:
        log_text = [
            [time_now, preprint_id, entry["username"],
             result.uri, result.cid]
        ]
        df = pd.DataFrame(
            log_text,
            columns=["utc", "scielo_preprint_id", "username", "uri", "cid"]
        )

    filename = entry[logname]
    if not filename:
        return None
    if os.path.exists(filename):
        df.to_csv(filename, mode="a", header=None, index=None)
    else:
        df.to_csv(filename, mode="w", index=None)


# retrieval of daily entries, and
# calling a sub process for new submissions and abstracts
def newentries(
    logfiles,
    cat,
    oai_set,
    client,
    update_limited,
    newsubmission_mode,
    abstract_mode,
    summary_mode,
    pt_mode,
    num_last_days=None,
):
    print("getting daily entries for " + cat)
    try:
        entries = aSd.daily_entries(cat, oai_set, utcnow(), num_last_days)
    except Exception:
        print("\n**error for retrieval**\nlabel: " + cat)
        traceback.print_exc()
        if summary_mode and not check_log_dates(
                cat, "post_summary_log", logfiles):
            # daily entries retrieval failed and
            # no summary for today has been posted.
            time_now = utcnow()
            ptext = intro(time_now, 0, cat)
            update_limited(
                logfiles,
                cat,
                client,
                "0",
                "",
                ptext,
                "",
                "",
                "",
                "",
                "post",
                pt_mode,
                [post_language_default],
            )
        return None

    if not newsubmission_mode:
        return None

    print("new submissions for " + cat)
    # The summary log is the mark of a run that has already happened
    # today, so it can only answer for a bot that posts summaries.
    # Without one, the post log alone keeps a preprint from being
    # announced twice, which is what a second run of a day would risk.
    if summary_mode and check_log_dates(cat, "post_summary_log", logfiles):
        print(cat + " already posted for today")
        return None

    # A harvest by datestamp returns updated preprints next to brand new
    # ones. The post log tells them apart, so an update never becomes a
    # second announcement.
    try:
        announced = announced_ids(cat, logfiles)
    except Exception:
        print("\n**error for post log**\nlabel: " + cat
              + "\nnothing posted, since an unreadable post log cannot "
              + "rule out a second announcement.")
        traceback.print_exc()
        return None

    records = entries.newsubmissions
    # a record with no identifier cannot be logged, so it cannot be kept
    # from a second announcement either.
    unidentified = [one for one in records if not one["id"]]
    for one in unidentified:
        print("skipping a record with no usable id for " + cat
              + ": " + one["oai_identifier"])

    fresh = [one for one in records
             if one["id"] and one["id"] not in announced]
    skipped = len(records) - len(fresh) - len(unidentified)
    if skipped > 0:
        print("skipping " + str(skipped)
              + " already announced record(s) for " + cat)

    newsub_entries = aSf.format(fresh)
    newsubmissions(
        logfiles,
        cat,
        client,
        update_limited,
        newsub_entries,
        abstract_mode,
        summary_mode,
        pt_mode,
    )


# the language tag of a post about one preprint. dc:language of the
# record is what chose the translation of the title and the abstract that
# a post carries, so it is the language of the post as well. A record
# that names no language it can use falls back on the default rather than
# claim a language it does not have.
def post_langs(language):
    return [language if language else post_language_default]


# an introductory text of each bot
# an example: [2026-07-25 Sat (UTC), 4 new preprints found for SciELO Preprints]
def intro(given_time, num, cat):
    ptext = "[" + given_time.strftime("%Y-%m-%d %a") + " (UTC), "
    if num == 0:
        ptext = ptext + "no new preprints found for "
    elif num == 1:
        ptext = ptext + str(num) + " new preprint found for "
    else:
        ptext = ptext + str(num) + " new preprints found for "
    ptext = ptext + cat

    if num > post_updates - 1:
        ptext = (
            ptext
            + ", but only first "
            + str(post_updates - 1)
            + " preprints to post."
            + "]"
        )
    else:
        ptext = ptext + "]"
    return ptext


# new submissions by posts and abstracts by replies
def newsubmissions(
    logfiles, cat, client, update_limited, entries, abstract_mode,
    summary_mode, pt_mode
):
    if summary_mode:
        time_now = utcnow()
        ptext = intro(time_now, len(entries), cat)
        update_limited(
            logfiles,
            cat,
            client,
            str(len(entries)),
            "",
            ptext,
            "",
            "",
            "",
            "",
            "post",
            pt_mode,
            [post_language_default],
        )
    else:
        print("no summary for " + cat + ", "
              + str(len(entries)) + " new preprint(s) to post")
    post_counter = 1

    for each in entries:
        if post_counter < post_updates:
            preprint_id = each["id"]
            langs = post_langs(each["language"])
            result = update_limited(
                logfiles,
                cat,
                client,
                "",
                preprint_id,
                each["post_text"],
                "",
                "",
                "",
                "",
                "post",
                pt_mode,
                langs,
            )
            post_counter += 1

            if abstract_mode and result:
                sep_abst = each["separated_abstract"]
                for i, partial_abst in enumerate(sep_abst):
                    if i == 0:
                        abst_result = update_limited(
                            logfiles,
                            cat,
                            client,
                            "",
                            preprint_id,
                            partial_abst,
                            result.uri,
                            result.cid,
                            result.uri,
                            result.cid,
                            "reply",
                            pt_mode,
                            langs,
                        )
                    else:
                        abst_result = update_limited(
                            logfiles,
                            cat,
                            client,
                            "",
                            preprint_id,
                            partial_abst,
                            result.uri,
                            result.cid,
                            abst_result.uri,
                            abst_result.cid,
                            "reply",
                            pt_mode,
                            langs,
                        )
                    if abst_result == 0:
                        break


# every preprint id this bot has already posted
def announced_ids(cat, logfiles):
    if not logfiles:
        return set()

    entry = log_entry(logfiles, cat, ["post_log", "username"])
    if entry is None:
        # a label logfiles.json does not carry cannot be checked against
        # a post log, and an unchecked label announces every revised
        # preprint again. Raising leaves this label unposted and lets the
        # rest of the run go on.
        raise Exception("no readable log file entry for " + cat)

    filename = entry["post_log"]
    if not os.path.exists(filename):
        print("log file does not exist: " + filename)
        return set()

    try:
        df = pd.read_csv(filename, dtype=object)
    except Exception:
        time_now = utcnow()
        error_text = "\nutc: " + str(time_now) + "\nfilename: " + filename
        error_text = "\n**error for log file**" + error_text
        print(error_text)
        traceback.print_exc()
        # an unreadable post log must not turn into a second round of
        # announcements.
        raise

    if "scielo_preprint_id" not in df.columns:
        raise Exception("no scielo_preprint_id column in " + filename)

    username = entry["username"]
    ids = df.loc[df["username"] == username, "scielo_preprint_id"]
    return set(one for one in ids.dropna().astype(str))


# true if this finds a today's post.
def check_log_dates(cat, logname, logfiles):
    if not logfiles:
        print("no log files")
        return False

    entry = log_entry(logfiles, cat, [logname, "username"])
    if entry is None:
        # nothing to read is not a post of today. What keeps this safe is
        # the post log, read before anything is posted: a label that has
        # no log file entry never reaches a post of a new submission.
        return False

    filename = entry[logname]
    if not os.path.exists(filename):
        print("log file does not exists: " + filename)
        return False

    time_now = utcnow()
    try:
        df = pd.read_csv(filename, dtype=object)
    except Exception:
        error_text = "\nutc: " + str(time_now) + "\nfilename: " + filename
        error_text = "\n**error for log file**" + error_text
        print(error_text)
        traceback.print_exc()
        return False
    for index, row in df.iterrows():
        log_time = datetime.fromisoformat(row["utc"])
        if (
            check_dates(log_time, time_now)
            and row["username"] == entry["username"]
        ):
            return True
    return False


# true if dates of input times are the same.
# SciELO Preprints publishes on any day of the week, so unlike arXiv
# there is no weekend to fold into a weekday.
def check_dates(time1, time2):
    return time1.date() == time2.date()


# a naive utc timestamp, as written to and read back from the log files
def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def atproto_client(keys):
    client = Client()
    try:
        time.sleep(bsky_createaccts_sleep)
        client.login(keys["username"], keys["password"])
    except Exception:
        print("\n**error: " + keys["username"] + " failed to login.")
        traceback.print_exc()
        return None
    return client


def atproto_uri_to_url(uri):
    if not uri:
        return ""
    path = uri[5:]
    parts = path.split("/", 1)
    did = parts[0]
    resource = parts[1]
    post_id = resource.split("/")[-1]
    return f"https://bsky.app/profile/{did}/post/{post_id}"


def generate_facets_for_urls(text):
    url_pattern = re.compile(r"https?://[^\s\[\]]+")
    facets = []

    for match in url_pattern.finditer(text):
        # convert character offsets to UTF-8 byte offsets
        byte_start = len(text[:match.start()].encode("utf-8"))
        byte_end = len(text[:match.end()].encode("utf-8"))
        url = match.group()

        facets.append(
            {
                "index": {
                    "byteStart": byte_start,
                    "byteEnd": byte_end,
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": url,
                    }
                ],
            }
        )
    return facets
