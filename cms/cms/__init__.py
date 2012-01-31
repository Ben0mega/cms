#!/usr/bin/python
# -*- coding: utf-8 -*-

# Programming contest management system
# Copyright © 2010-2012 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2012 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Load the configuration.

"""

import os
import simplejson as json
from argparse import ArgumentParser

from cms.async import ServiceCoord, Address, Config


def load_config_file(cmsconf):
    """Populate the Config class with everything that sits inside the
    JSON file cmsconf (usually something/etc/cms.conf). The only
    pieces of data treated differently are the elements of
    core_services and other_services.

    Also, add a boolean field '_installed' that discerns if the
    program is run from the repository or from the installed
    package. To do so, it check if sys.argv[0] is in /usr/.

    Finally, add _*_dir for specific directories used by the services.

    cmsconf (string): the path of the JSON config file

    """
    # Load config file
    try:
        dic = json.load(open(cmsconf))
    except json.decoder.JSONDecodeError:
        print "Unable to load JSON configuration file %s " \
              "because of a JSON decoding error. Aborting." % cmsconf
        import sys
        sys.exit(1)

    # Put core and test services in Config
    for service in dic["core_services"]:
        for shard_number, shard in enumerate(dic["core_services"][service]):
            Config.core_services[ServiceCoord(service, shard_number)] = \
                Address(*shard)
    del dic["core_services"]

    for service in dic["other_services"]:
        for shard_number, shard in enumerate(dic["other_services"][service]):
            Config.other_services[ServiceCoord(service, shard_number)] = \
                Address(*shard)
    del dic["other_services"]

    # Put everything else. Note that we re-use the Config class, which
    # async thinks it is just for itself. This should cause no
    # problem, though, since Config's usage by async is very
    # read-only.
    for key in dic:
        setattr(Config, key, dic[key])

    # Put also the _installed data.
    import sys
    Config._installed = sys.argv[0].startswith("/usr/") and \
        sys.argv[0] != '/usr/bin/ipython' and \
        sys.argv[0] != '/usr/bin/python'

    if Config._installed:
        Config._log_dir = os.path.join("/", "var", "local", "log", "cms")
        Config._cache_dir = os.path.join("/", "var", "local", "cache", "cms")
        Config._data_dir = os.path.join("/", "var", "local", "lib", "cms")
    else:
        Config._log_dir = "log"
        Config._cache_dir = "cache"
        Config._data_dir = "lib"


CONFIGURATION_FILES = [os.path.join(".", "examples", "cms.conf"),
                       os.path.join("/", "etc", "cms.conf"),
                       os.path.join("/", "usr", "local", "etc", "cms.conf")]

for conffile in CONFIGURATION_FILES:
    try:
        load_config_file(conffile)
    except IOError:
        pass
    else:
        break
else:
    print "Could not find JSON configuration file in any of the following locations:\n"
    for path in CONFIGURATION_FILES:
        print "    %s" % path
    print "\nAborting."
    import sys
    sys.exit(1)


def default_argument_parser(description, cls, ask_contest=None):
    """Default argument parser for services - in two versions: needing
    a contest_id, or not.

    description (string): description of the service.
    cls (class): service's class.
    ask_contest (function): None if the service does not require a
                            contest, otherwise a function that returns
                            a contest_id (after asking the admins?)

    return (object): an instance of a service.

    """
    parser = ArgumentParser(description=description)
    parser.add_argument("shard", type=int)

    # We need to allow using the switch "-c" also for services that do
    # not need the contest_id because RS needs to be able to restart
    # everything without knowing which is which.
    contest_id_help = "id of the contest to automatically load"
    if ask_contest is None:
        contest_id_help += " (ignored)"
    parser.add_argument("-c", "--contest-id", help=contest_id_help,
                        nargs="?", type=int)
    args = parser.parse_args()
    if ask_contest is not None:
        if args.contest_id is not None:
            return cls(args.shard, args.contest_id)
        else:
            return cls(args.shard, ask_contest())
    else:
        return cls(args.shard)
