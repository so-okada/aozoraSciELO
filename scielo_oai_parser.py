#!/usr/bin/env python3
# written by So Okada so.okada@gmail.com
# a simple OAI-PMH harvester of SciELO Preprints for aozoraSciELO
# https://github.com/so-okada/aozoraSciELO/

import re
import html
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from ratelimit import limits, sleep_and_retry

from aozoraSciELO_variables import *

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
OAI_DC_NS = "http://www.openarchives.org/OAI/2.0/oai_dc/"
DC_NS = "http://purl.org/dc/elements/1.1/"
XML_NS = "http://www.w3.org/XML/1998/namespace"

# an empty answer to a date range is a normal answer, not a failure.
EMPTY_ERRORS = ["noRecordsMatch"]


class retrieve:
    """One OAI-PMH ListRecords harvest of SciELO Preprints.

    A harvest asks for records stamped on or after from_date, and takes
    everything up to the present. SciELO Preprints stamps a record when
    it is posted and again whenever it is updated, so a harvest mixes
    brand-new preprints with revised ones. This parser does not try to
    tell them apart: it returns every record it finds and leaves the
    decision of what is new to the post log, which is the only durable
    record of what has been announced already.

    There is deliberately no until_date. As of 2026-07, the SciELO
    Preprints endpoint answers any request carrying `until` with a
    bodyless HTTP 500, whether `until` travels with `from` or alone,
    while `from` by itself is served normally. An open-ended range is
    what a daily bot wants anyway, so this costs nothing.
    """

    def __init__(self, label, oai_set="", from_date=""):
        records = []
        deleted = []
        pages = 0
        resumption_token = None

        while True:
            if resumption_token:
                # a resumptionToken must travel alone.
                params = {"verb": "ListRecords",
                          "resumptionToken": resumption_token}
            else:
                params = {"verb": "ListRecords",
                          "metadataPrefix": oai_metadata_prefix}
                if oai_set:
                    params["set"] = oai_set
                if from_date:
                    params["from"] = from_date

            content = oai_request(params)
            pages += 1
            root = ET.fromstring(content)

            error = root.find(f"{{{OAI_NS}}}error")
            if error is not None:
                code = error.get("code", "")
                if code in EMPTY_ERRORS:
                    break
                raise OAIProtocolError(
                    "OAI error for " + label + ": "
                    + code + " " + (error.text or "").strip())

            for record in root.iter(f"{{{OAI_NS}}}record"):
                header = record.find(f"{{{OAI_NS}}}header")
                if header is None:
                    continue
                identifier = text_of(header.find(f"{{{OAI_NS}}}identifier"))
                # a withdrawn preprint has no metadata to announce.
                if header.get("status") == "deleted":
                    deleted.append(identifier)
                    continue
                entry = parse_record(label, record, header, identifier)
                if entry:
                    records.append(entry)

            token_element = root.find(
                f"{{{OAI_NS}}}ListRecords/{{{OAI_NS}}}resumptionToken")
            resumption_token = text_of(token_element)
            # an empty or absent resumptionToken closes the list.
            if not resumption_token:
                break
            if pages >= oai_max_pages:
                print("reached oai_max_pages of " + str(oai_max_pages)
                      + " for " + label + ", stopping the harvest")
                break
            time.sleep(oai_page_sleep)

        self.label = label
        self.oai_set = oai_set
        self.from_date = from_date
        self.pages = pages
        self.deleted = deleted
        self.records = records
        # every harvested record is a candidate announcement.
        self.newsubmissions = records
        self.total = len(records)


# an OAI error carried by the protocol itself, such as badArgument. It
# fails the same way on every try, so a retry only wastes time.
class OAIProtocolError(Exception):
    pass


# one http attempt at the OAI endpoint. Every request of a run passes
# here, a retried one included, so this is the single place a ceiling can
# hold whatever asked for the request: a page loop, a retry, or one bot
# after another. The sleeps elsewhere each pace one code path and none of
# them knows the total, which is what lets a retry storm outrun them.
@sleep_and_retry
@limits(calls=oai_calls, period=oai_call_period)
def oai_call(request):
    with urllib.request.urlopen(request, timeout=oai_timeout) as r:
        return r.read()


# an OAI request that honours the 503 flow control of the protocol
def oai_request(params):
    url = oai_base_url + "?" + urllib.parse.urlencode(params)
    # the request line is the first thing to check when a harvest fails.
    print("OAI request: " + url)
    request = urllib.request.Request(
        url, headers={"User-Agent": oai_user_agent})

    for trial in range(oai_max_trial + 1):
        try:
            return oai_call(request)
        except urllib.error.HTTPError as e:
            # a failing server explains itself in the response body, so
            # show it instead of leaving a bare status code behind.
            body = error_body(e)
            print("**OAI http error " + str(e.code) + " " + str(e.reason)
                  + "\nurl: " + url
                  + ("\nbody: " + body if body else ""))
            # 503 with Retry-After is how an OAI server asks a harvester
            # to slow down. Waiting is the correct answer, not a retry
            # storm, and not an error.
            if e.code in oai_retry_http_codes and trial < oai_max_trial:
                wait = retry_after(e.headers.get("Retry-After"))
                print("retrying in " + str(wait) + "s")
                time.sleep(wait)
                continue
            if e.code not in oai_retry_http_codes:
                # a client error is our own doing: the verb, the set, or
                # the dates. Retrying cannot fix it.
                raise OAIProtocolError(
                    "http " + str(e.code) + " for " + url
                    + (": " + body if body else "")) from e
            raise


def error_body(e):
    try:
        raw = e.read(oai_error_body_len * 4)
    except Exception:
        return ""
    text = raw.decode("utf-8", "replace")
    # an html error page reads as noise unless it is flattened first.
    return clean(text)[:oai_error_body_len]


def retry_after(value):
    if value and value.strip().isdigit():
        # cap a hostile or mistaken Retry-After.
        return min(int(value.strip()), oai_call_sleep)
    return oai_page_sleep


def parse_record(label, record, header, identifier):
    metadata = record.find(f"{{{OAI_NS}}}metadata")
    if metadata is None:
        return None
    dc = metadata.find(f"{{{OAI_DC_NS}}}dc")
    if dc is None:
        return None

    # the language of the record picks one translation out of the
    # repeated dc fields, so it has to be known first.
    lang = language(dc_values(dc, "language"))

    title_lang, titles = chosen_group(dc_elements(dc, "title"), lang)
    if not titles:
        return None

    identifiers = dc_values(dc, "identifier")
    entry = {}
    entry["label"] = label
    entry["oai_identifier"] = identifier
    entry["id"] = short_id(identifier, identifiers)
    entry["datestamp"] = text_of(header.find(f"{{{OAI_NS}}}datestamp"))
    entry["sets"] = [text_of(one) for one
                     in header.findall(f"{{{OAI_NS}}}setSpec")]
    entry["title"] = titles[0]
    entry["authors"] = author_separator.join(
        values_in_language(dc_elements(dc, "creator"), lang))
    # what a post is tagged with, so the tag agrees with the title and the
    # abstract the post carries, whether dc:language chose them or the
    # first language group did.
    entry["language"] = lang or title_lang
    entry["abstract"] = first(
        values_in_language(dc_elements(dc, "description"), lang))
    entry["subjects"] = ", ".join(
        values_in_language(dc_elements(dc, "subject"), lang))
    entry["date"] = clean(first(dc_values(dc, "date")))
    entry["url"] = url_of(identifiers, entry["id"])
    # kept as metadata of the record. A post links the view url only.
    entry["doi"] = doi_of(identifiers, entry["id"])
    return entry


def dc_values(dc, name):
    return [one.text for one in dc.findall(f"{{{DC_NS}}}{name}")
            if one.text and one.text.strip()]


def dc_elements(dc, name):
    return [one for one in dc.findall(f"{{{DC_NS}}}{name}")
            if one.text and one.text.strip()]


# a two letter tag out of an xml:lang such as pt-BR
def lang_of(element):
    tag = (element.get(f"{{{XML_NS}}}lang") or "").lower()
    return re.split(r"[-_]", tag)[0]


# SciELO Preprints repeats dc:title, dc:creator, dc:subject and
# dc:description once per interface language, so a paper by two authors
# arrives with six dc:creator elements. Taking them all would post the
# author list three times over. Prefer the values tagged with the
# language of the record, fall back on the first language group, and
# dedupe what is left in case a group repeats a name.
def values_in_language(elements, lang):
    return chosen_group(elements, lang)[1]


# the language group a field is read in, and its values. The key is worth
# having on its own: a record whose dc:language names no language we can
# use still has to be tagged with the language its title was read in, or
# bluesky is told one language while the post carries another.
#
# SciELO Preprints accepts Spanish, English and Portuguese, and a
# submission in either of the other two must carry an English title and
# abstract as well. English is therefore the one group a record can be
# counted on to have, which makes it the fallback when dc:language names
# nothing usable: a group chosen for being first in the document would
# depend on an order the repository never promised.
def chosen_group(elements, lang):
    groups = {}
    order = []
    for one in elements:
        key = lang_of(one)
        if key not in groups:
            groups[key] = []
            order.append(key)
        value = clean(one.text)
        if value:
            groups[key].append(value)

    if lang and groups.get(lang):
        chosen_key, chosen = lang, groups[lang]
    elif groups.get(post_language_default):
        chosen_key, chosen = (post_language_default,
                              groups[post_language_default])
    else:
        chosen_key, chosen = next(
            ((key, groups[key]) for key in order if groups[key]), ("", []))

    seen = set()
    result = []
    for one in chosen:
        if one not in seen:
            seen.add(one)
            result.append(one)
    return chosen_key, result


def text_of(element):
    if element is None or not element.text:
        return ""
    return element.text.strip()


def first(values):
    return values[0] if values else ""


# an OAI identifier such as oai:ops.preprints.scielo.org:preprint/1234
# carries the preprint number in its last segment.
def short_id(identifier, identifiers):
    if identifier:
        tail = identifier.split(":")[-1].split("/")[-1].strip()
        if tail:
            return tail
    # fall back on the view url, then on the doi.
    for one in identifiers:
        found = re.search(r"/view/(\d+)", one)
        if found:
            return found.group(1)
    for one in identifiers:
        found = re.search(r"[Pp]reprints?\.(\d+)", one)
        if found:
            return found.group(1)
    return ""


def url_of(identifiers, short):
    for one in identifiers:
        one = one.strip()
        if "/preprint/view/" in one and one.startswith("http"):
            return one
    for one in identifiers:
        one = one.strip()
        if one.startswith("http") and "doi.org" not in one:
            return one
    if short:
        return ("https://preprints.scielo.org/index.php/scielo/preprint/view/"
                + short)
    return ""


# A record can carry more than one doi. SciELO Preprints mints its own
# as 10.<prefix>/SciELOPreprints.<id>, and a record tied to a journal can
# carry that journal's doi as well, which is not necessarily registered
# at doi.org yet. An announcement of a preprint should link the doi of
# the preprint, so take that one whenever the record offers it.
def doi_of(identifiers, short=""):
    dois = []
    for one in identifiers:
        found = re.search(r"(10\.\d{4,9}/\S+)", one.strip())
        if found:
            dois.append(found.group(1).rstrip(".,;"))
    if not dois:
        return ""

    if short:
        for one in dois:
            if one.lower().endswith("scielopreprints." + short.lower()):
                return one
    for one in dois:
        if "scielopreprints" in one.lower():
            return one

    return dois[0]


# a two letter language tag out of values such as pt, pt-BR, or por
def language(values):
    value = clean(first(values)).lower()
    if not value:
        return ""
    value = re.split(r"[-_]", value)[0]
    three_to_two = {"por": "pt", "spa": "es", "eng": "en"}
    if value in three_to_two:
        return three_to_two[value]
    if re.fullmatch(r"[a-z]{2}", value):
        return value
    return ""


# OJS metadata carries html markup and character references.
def clean(text):
    if not text:
        return ""
    # OJS escapes markup once, and sometimes twice, so a title can hold
    # "<i>" as text and "&lt;i&gt;" as entities at the same time. One
    # pass catches only one form, so unescape and strip again until the
    # text stops changing. A species name arrives in italics often
    # enough that a stray "<i>" in a post is not hypothetical.
    text = strip_markup(text)
    for round in range(unescape_rounds):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = strip_markup(unescaped)
    # non breaking spaces and friends read as spaces in a post.
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_markup(text):
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</p\s*>|</div\s*>|</li\s*>", " ", text)
    # only a recognisable tag, so that "a < b" survives as arithmetic.
    return re.sub(r"(?i)</?[a-z][a-z0-9]*(\s[^<>]*)?/?>", "", text)
