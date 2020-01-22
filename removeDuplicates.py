#!/bin/python2

import sys, os, time
import wbackup

from pprint import pprint as pp
from glob import glob
import random, time
import os
import math
from multiprocessing import Pool


wbackup.runOnlyOnce( __file__ )


jobs = wbackup.jobCards(justCards=True)


jobs._cards_remove_duplicated('0693.omo_sou')
