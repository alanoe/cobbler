"""
Validates rendered automatic OS installation files.

Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import os

import clogger
import kickgen
import utils


class Validate:

    def __init__(self, collection_mgr, logger=None):
        """
        Constructor
        """
        self.collection_mgr = collection_mgr
        self.settings = collection_mgr.settings()
        self.kickgen = kickgen.KickGen(collection_mgr)
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger


    def run(self):
        """
        Returns True if there are no errors, otherwise False.
        """

        if not os.path.exists("/usr/bin/ksvalidator"):
            utils.die(self.logger, "ksvalidator not installed, please install pykickstart")

        failed = False
        for x in self.collection_mgr.profiles():
            (result, errors) = self.checkfile(x, True)
            if not result:
                failed = True
            if len(errors) > 0:
                self.log_errors(errors)
        for x in self.collection_mgr.systems():
            (result, errors) = self.checkfile(x, False)
            if not result:
                failed = True
            if len(errors) > 0:
                self.log_errors(errors)

        if failed:
            self.logger.warning("*** potential errors detected in automatic installation files ***")
        else:
            self.logger.info("*** all automatic installation files seem to be ok ***")

        return not(failed)

    def checkfile(self, obj, is_profile):
        last_errors = []
        blended = utils.blender(self.collection_mgr.api, False, obj)

        os_version = blended["os_version"]

        self.logger.info("----------------------------")
        self.logger.debug("osversion: %s" % os_version)

        ks = blended["autoinst"]
        if ks is None or ks == "":
            self.logger.info("%s has no autoinst, skipping" % obj.name)
            return [True, last_errors]

        breed = blended["breed"]
        if breed != "redhat":
            self.logger.info("%s has a breed of %s, skipping" % (obj.name, breed))
            return [True, last_errors]

        server = blended["server"]
        if not ks.startswith("/"):
            url = ks
        else:
            if is_profile:
                url = "http://%s/cblr/svc/op/autoinst/profile/%s" % (server, obj.name)
                self.kickgen.generate_autoinstall_for_profile(obj.name)
            else:
                url = "http://%s/cblr/svc/op/autoinst/system/%s" % (server, obj.name)
                self.kickgen.generate_autoinstall_for_system(obj.name)
            last_errors = self.kickgen.get_last_errors()

        self.logger.info("checking url: %s" % url)

        rc = utils.subprocess_call(self.logger, "/usr/bin/ksvalidator -v \"%s\" \"%s\"" % (os_version, url), shell=True)
        if rc != 0:
            return [False, last_errors]

        return [True, last_errors]


    def log_errors(self, errors):
        self.logger.warning("Potential templating errors:")
        for error in errors:
            (line, col) = error["lineCol"]
            line -= 1   # we add some lines to the template data, so numbering is off
            self.logger.warning("Unknown variable found at line %d, column %d: '%s'" % (line, col, error["rawCode"]))
