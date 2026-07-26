#!/usr/bin/env python3
# written by So Okada so.okada@gmail.com
# a part of aozoraSciELO for formatting SciELO Preprints metadata
# https://github.com/so-okada/aozoraSciELO/

import re
from nameparser import HumanName
from aozoraSciELO_variables import *


# format all new submissions
def format(entries):
    return [format_each(one) for one in entries]


# format each new submission
def format_each(orig_entry):
    entry = orig_entry.copy()
    # unlike arXiv, a SciELO Preprints url has no fixed length, so the
    # room left for a title and authors is measured per preprint.
    entry["tail"] = tail(entry)
    fixed_length = len(list(entry["tail"])) + newsub_spacer + margin
    orig_title = entry["title"]

    authors_title = entry["authors"] + entry["title"]
    current_len = len(list(authors_title)) + fixed_length

    # first, a title
    if current_len > max_len:
        difference = current_len - max_len
        current_len_title = len(list(entry["title"]))
        lim = max(min_len_title, current_len_title - difference)
        entry["title"] = simple(entry["title"], lim)

    authors_title = entry["authors"] + entry["title"]
    current_len = len(list(authors_title)) + fixed_length

    # second, authors
    if current_len > max_len:
        difference = current_len - max_len
        current_len_authors = len(list(entry["authors"]))
        lim = max(min_len_authors, current_len_authors - difference)
        entry["authors"] = authors(entry["authors"], lim)

    # third, a longer title if the length of authors' names becomes shorter
    entry["title"] = orig_title
    authors_title = entry["authors"] + entry["title"]
    current_len = len(list(authors_title)) + fixed_length

    if current_len > max_len:
        difference = current_len - max_len
        current_len_title = len(list(entry["title"]))
        lim = max(min_len_title, current_len_title - difference)
        entry["title"] = simple(entry["title"], lim)

    entry["post_text"] = post_text(entry)
    entry["separated_abstract"] = separate_abstract(
        entry["abstract"], entry["url"])
    return entry


# the part of a post that must survive in full: the link that lets a
# reader reach the preprint. The doi is deliberately left out, since it
# points at the same preprint as the view url and a record bound for a
# journal can carry a doi that doi.org does not resolve. The language of
# a record still chooses which translation of a title and an abstract to
# post, it just is not spelled out in the post.
def tail(entry):
    return entry["url"]


def post_text(entry):
    prefix = entry["authors"] + ": " if entry["authors"] else ""
    text = prefix + entry["title"]
    if entry["tail"]:
        text = text + " " + entry["tail"] if text else entry["tail"]
    return text


# a simple text cut
def simple(orig, lim):
    orig = orig.strip()
    wlen = len(list(orig))
    if wlen <= lim:
        return orig

    while wlen > lim:
        orig = orig[:-1]
        wlen = len(list(orig))

    return orig[:-3] + "..."


# formating authors' names
def authors(orig, lim):
    if lim < 1:
        return ""
    if len(list(orig)) <= lim:
        return orig

    no_paren = noparen(orig)
    if len(list(no_paren)) <= lim:
        return no_paren

    sr_names = surnames(no_paren)
    if len(list(sr_names)) <= lim:
        return sr_names

    et_al = etal(no_paren)
    if len(list(et_al)) <= lim:
        return et_al

    return ""


def noparen(test_str):
    ret = ""
    skip = 0
    for i in test_str:
        if i == "(":
            skip += 1
        elif i == ")":
            skip -= 1
        elif skip == 0:
            ret += i
    ret = re.sub(r"[ ]+;", ";", ret)
    ret = re.sub(r"[ ]+$", "", ret)
    return ret


# cf. https://stackoverflow.com/questions/14596884/remove-text-between-and-in-python/14598135#14598135


def surnames(orig):
    names = orig.split(author_separator.strip())
    sr_names = [surname(one) for one in names if one.strip()]
    return author_separator.join(sr_names)


def surname(name):
    name = name.strip()
    # an inverted name gives its family name away before the comma.
    if "," in name:
        return name.split(",")[0].strip() or name
    return HumanName(name).last or name


def etal(orig):
    names = orig.split(author_separator.strip())
    first_author = names[0].strip()
    return first_author + ", et al."


# separate an abstract with a counter and a url tag
def separate_abstract(orig, url):
    # abst_tag reserves room for a two digit counter on both sides, so a
    # tag never eats into the abstract it labels.
    lim = max_len - abst_tag - len(list(url)) - margin
    if lim < 1:
        return []
    sep_abstract = separate(orig, lim)
    num = len(list(sep_abstract))
    result = []
    for i, each in enumerate(sep_abstract):
        ptext = (
            each
            + " ["
            + str(i + 1)
            + "/"
            + str(num)
            + " of "
            + url
            + "]"
        )
        result.append(ptext)
    return result


# separate a text by weighted lengths <=lim
def separate(orig, lim):
    sep_text = []
    orig = orig.strip() if orig else ""

    # no inf loop
    if any(len(list(t)) > lim for t in orig.split(" ")):
        print(
            "\n**cannot separate** \
        \nmax weighted length:  "
            + str(lim)
            + " \ninput:  "
            + orig
        )
        return sep_text

    while orig:
        partial_text = orig
        wlen = len(list(partial_text))
        while wlen > lim:
            partial_text = partial_text.rsplit(" ", 1)[0]
            wlen = len(list(partial_text))
        sep_text.append(partial_text.strip())
        orig = orig[len(list(partial_text)):].strip()
    return sep_text
