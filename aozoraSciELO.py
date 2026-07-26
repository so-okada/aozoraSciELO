#!/usr/bin/env python3
# written by So Okada so.okada@gmail.com
# a main interface of aozoraSciELO
# https://github.com/so-okada/aozoraSciELO/

import json
import argparse
import traceback
from aozoraSciELO_variables import (oai_from_days,
                                   oai_from_days_upper_limit)
import aozoraSciELO_post as aSp

parser = argparse.ArgumentParser(
    description='SciELO Preprints daily new submissions by posts, '
    'daily summaries by posts, '
    'and abstracts by replies.')
parser.add_argument("--switches_keys",
                    "-s",
                    required=True,
                    default='',
                    help="output switches and api keys in json")
parser.add_argument("--logfiles",
                    "-l",
                    default='',
                    help="log file names in json")
parser.add_argument("--num_last_days",
                    "-n",
                    type=int,
                    default=None,
                    help="how many last days to fetch, "
                    "0 for today alone, "
                    "oai_from_days_upper_limit at most. "
                    "oai_from_days of "
                    "aozoraSciELO_variables.py when omitted")
parser.add_argument("--mode",
                    "-m",
                    choices=[0, 1],
                    type=int,
                    default='0',
                    help='1 for bsky and 0 for stdout only')


args = parser.parse_args()
switches = args.switches_keys
logfiles = args.logfiles
num_last_days = args.num_last_days
pt_mode = args.mode

if num_last_days is not None and num_last_days < 0:
    raise Exception('num_last_days cannot be negative')

# The reach is capped here, before a login and before a harvest, so that
# an oversized one cannot be mistaken for a harvest that found nothing.
from_days = oai_from_days if num_last_days is None else num_last_days
if from_days > oai_from_days_upper_limit:
    raise Exception(
        'a reach of ' + str(from_days) + ' days exceeds '
        'oai_from_days_upper_limit of ' + str(oai_from_days_upper_limit))


try:
    f = open(switches)
except Exception:
    traceback.print_exc()
    raise Exception('can not obtain output switches and api keys')
switches = json.load(f)

if logfiles:
    try:
        f = open(logfiles)
    except Exception:
        traceback.print_exc()
        raise Exception('can not obtain log filenames')
    logfiles = json.load(f)

aSp.main(switches, logfiles, pt_mode, num_last_days)
