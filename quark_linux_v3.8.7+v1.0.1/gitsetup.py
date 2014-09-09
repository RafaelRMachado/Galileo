#!/usr/bin/env python

# Copyright(c) 2013 Intel Corporation.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.

# John Toomey / Marc Herbert

from __future__ import print_function
import os
import sys
#import logging
import subprocess
from optparse import OptionParser
from ConfigParser import ConfigParser, NoOptionError

def get_or_none(cfg, secname, propname):
    '''Converts an exception into None'''
    try:
         return cfg.get(secname, propname)
    except NoOptionError:
         return None

def get_options():
    '''Process the command line args'''

    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option('-c', '--config', action='store', dest='config',
                      default='upstream.cfg')
    parser.add_option('-u', '--url', action='store', dest='url',
                      help = "override server location with another (faster) mirror")
    parser.add_option('-d', '--depth', action='store', type='int', dest='depth',
                      default=3,
                      help = ("passed to git fetch to speed up the download. "
                              "Defaults to 3; set to 0 to disable. Requires a tag." )
                      )
    parser.add_option('--new-files-only', action='store_true', dest='new_files_only',
                      help = "Stops immediately after extracting brand new files " +
                      "from the patch(es)"
                      )

    (opts, _) = parser.parse_args()
    return opts

def run_command(command):
    print('Running: ' + command)
    subprocess.check_call(command, shell=True)


def extract_newfiles(patches):

    for p in patches:

        dname = "new-files-from-patch-" + p[:-len('.patch')]
        print (dname)
        os.mkdir(dname)
        
        run_command('cd %s && >/dev/null patch --force -p1 < ../%s; test $? -lt 2' %
                    ( dname, p ) )

def main():

    opts = get_options()

    config = ConfigParser()
    if os.path.isfile(opts.config):
        config.read(opts.config)
    else:
        print('Config file doesnt exist: %s' % opts.config)
        sys.exit(-1)

    patches = [ p for p in os.listdir('.') if p.endswith('.patch') ]
    # Python orders characters based on Unicode codepoints, see
    # Reference->Expressions->Comparisons.
    patches.sort()

    extract_newfiles(patches)

    if opts.new_files_only:
        return

    packagename = config.get('upstream', 'NAME')
    workdir = 'work'
    url = opts.url if opts.url else config.get('upstream', 'URL')
    tag = get_or_none(config, 'upstream', 'TAG')
    sha = get_or_none(config, 'upstream', 'SHA')
    gitref = "tags/" + tag if tag else sha

    if os.path.isdir(workdir):
        print('ERROR: Directory already exists: %s' % workdir)
        sys.exit(-1)

    if tag:
        os.mkdir(workdir)
        os.chdir(workdir)
        run_command('git init')
        run_command('git remote add origin %s' % url)
        fetchspec = "%s:%s" % (gitref, gitref)
        run_command('git fetch origin --depth=%s %s' % (opts.depth, fetchspec))
    else:
        # We cannot use --depth here. Part of the explanation:
        # http://thread.gmane.org/gmane.comp.version-control.git/73368/focus=73994
        run_command('git clone %s %s' % (url, workdir))
        os.chdir(workdir)

    run_command('git checkout -b clanton %s' % gitref)

    print('Applying patches, in this order: ' + str(patches))
    for p in patches:

        # We could probably use a better detection logic.
        if p.endswith('-quark.patch'):
            run_command('git am "../%s"' % p)
        else:
        # Need two steps since not every patch is a full git commit
            run_command('git apply --index "../%s"' % p)
            run_command('git commit -m "%s"' % p)


    if sha and tag and not opts.depth:
        git_rparse_cmd = 'test "$(git rev-parse %s~0)" = "%s"' % ( gitref, sha.strip() )
        run_command(git_rparse_cmd)

if __name__ == '__main__':
    main()
