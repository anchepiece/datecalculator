#!/usr/bin/env python
#
# Copyright (c) 2010 anchepiece
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
# * Neither the name of the owner nor the names of its contributors may
#   be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#
# This script is written in Python and released to the open source
# community for continuous improvements under the BSD 2.0 new
# license, which can be found at:
#
#   http://www.opensource.org/licenses/bsd-license.php
#

#
# The main DateCalculator class which handles gui creation, functions,
# and shutdown.  Handle all command line options here.
#

import os
import re
import sys
import math
import time
import logging
logger = logging.getLogger(__name__)
from datetime import datetime, date

__version__ = '0.1.2'
__fullname__ = 'DateCalculator'
__usage__ = \
"""
A simple script to provide a simple, easy to use interface to calculate a span
of time between two dates.  To be able to calculate a future date based on a
span of time.  To illustrate the difference in time using conventional methods
that are technically accurate.

Usage: python datecalculator.py --help --version --quiet --debug
            --help, displays usage message
            --version, shows current running version
            --quiet, hides all console messages
            --debug, run in debugging mode
"""

if __name__ == '__main__':
    print __usage__
    exit()

class DateCalculator(object):

    _application = None
    format = '%m/%d/%Y'

    def __init__(self):
        """
            Initializes DateCalculator
        """

        self.flags = self.get_command_flags(sys.argv[1:])

        # Show Version
        if self.flags.has_key('version'):
            self.version()

        # Show Help
        if self.flags.has_key('help'):
            self.help()

        # set up logging
        self.setup_logging()

        logger.info("Loading DateCalculator %s..." % __version__)
        self.main_init()

        if not self.flags.has_key('nogui'):
            logger.info("Loading interface...")
            import gtk
            # use GtkBuilder to build our interface from the XML file
            try:
                self.builder = gtk.Builder()
                main_ui = 'resources/ui/main.ui'
                self.builder.add_from_file(main_ui)
            except:
                logger.error("Failed to load UI file: %s" %  main_ui)
                sys.exit(1)

            try:
                self.window = self.builder.get_object('MainWindow')
                self.window.connect('destroy', self.on_window_destroy)

                self.calendar_start = self.builder.get_object('calendar_start')
                self.calendar_start.connect('day_selected', self.on_calendar_start_day_selected)

                self.calendar_end = self.builder.get_object('calendar_end')
                self.calendar_end.connect('day_selected', self.on_calendar_end_day_selected)

                self.today_start = self.builder.get_object('today_start')
                self.today_end = self.builder.get_object('today_end')

                self.eventbox_today_start = self.builder.get_object('eventbox_today_start')
                self.eventbox_today_start.connect('button-press-event', self.on_eventbox_today_start_button_press_event)
                #self.eventbox_today_start.set_events(gtk.gdk.BUTTON_PRESS_MASK)

                self.eventbox_today_end = self.builder.get_object('eventbox_today_end')
                self.eventbox_today_end.connect('button-press-event', self.on_eventbox_today_end_button_press_event)

                self.entry_start = self.builder.get_object('entry_start')
                self.entry_end = self.builder.get_object('entry_end')

                self.entry_from = self.builder.get_object('entry_from')
                self.entry_to = self.builder.get_object('entry_to')


                self.entry_days = self.builder.get_object('entry_days')
                self.entry_months = self.builder.get_object('entry_months')
                self.entry_years = self.builder.get_object('entry_years')

            except AttributeError as (e):
                logger.error("Failed loading UI element")
                logger.error(e)
                sys.exit(1)

            def set_readonly(w):
                if hasattr(w, "get_children"):
                    for child in w.get_children():
                        set_readonly(child)
                        if isinstance(child, gtk.Entry) and not child.get_editable():
                            child.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#cccccc"))
            set_readonly(self.window)

            # connect signals
            self.builder.connect_signals(self)
            self.gui_init()

            # set the default icon to the GTK "edit" icon
            gtk.window_set_default_icon_name(gtk.STOCK_EDIT)

            logger.info("Loading main window")
            if self.window:
                self.window.set_title('%s %s' % (__fullname__, __version__) )
                self.window.show_all()
            #start the gui
            self.main()

        DateCalculator._application = self

        # On SIGTERM, quit normally.
        import signal
        signal.signal(signal.SIGTERM, (lambda sig, stack: self.quit()))
    #end def __init__

    def get_command_flags(self, args):
      """
      Parse command line flags per specified usage, pick off key, value pairs
      All flags of type "--key=value" will be processed as __flags[key] = value,
                        "--option" will be processed as __flags[option] = option
      """
      flags   = {}
      rkeyval = '--(?P<key>\S*)[=](?P<value>\S*)' # --key=val
      roption = '--(?P<option>\S*)'               # --key
      r = '(' + rkeyval + ')|(' + roption + ')'
      rc = re.compile(r)
      for a in args:
        try:
          rcg = rc.search(a).groupdict()
          if rcg.has_key('key'):
            flags[rcg['key']] = rcg['value']
          if rcg.has_key('option'):
            flags[rcg['option']] = rcg['option']
        except AttributeError:
          return None
      return flags
    #end def get_command_flags

    def setup_logging(self):
        console_format = "%(levelname)-8s: %(message)s"
        loglevel = logging.INFO
        datefmt = "%H:%M:%S"
        if self.flags.has_key('debug'):
            loglevel = logging.DEBUG
            console_format = "%(asctime)s,%(msecs)3d:" + console_format
            console_format += " (%(name)s)" # add module name
        elif self.flags.has_key('quiet'):
            loglevel = logging.WARNING

        # Logging to terminal
        logging.basicConfig(level=loglevel, format=console_format,
                datefmt=datefmt)
    #end def setup_logging

    def version(self):
        print r"""
         _           __
        | \ _ _|_ _ /   _  |  _     |  _ _|_ _  __
        |_/(_| |_(/_\__(_| | (_ |_| | (_| |_(_) |   v%s

        """ % __version__
        exit()
    #end def version

    def get_version(self):
        """
            Returns the current version
        """
        return __version__
    #end def get_version

    def help(self):
        print __usage__
        exit()
    #end def version

    def close_logger(self):
        logger.info("%s is shutting down..." % __fullname__)
        logger.info("Bye!")
        logging.shutdown()
    #end def close_logger

    def quit(self):
        """
            Exits normally.
        """
        self.close_logger()
        import gtk
        gtk.main_quit()
        exit()
    #end def quit

    def main(self):
        """
            Runs the gtk main loop
        """
        import gtk
        try:
            gtk.main()
        except KeyboardInterrupt:
            self.on_keyboard_interrupt()
    #end def main

    def main_init(self):
        """
            Initializes start and end date to today's date
        """
        today = datetime.today()
        # today = datetime.fromtimestamp(time.time())
        self.start_date  = today
        self.end_date    = today
        self.diff_days   = int(0)
        self.diff_months = int(0)
        self.diff_years  = int(0)
    #end def init_dates

    #
    # gui
    #
    def gui_init(self):
        """
            Initializes the gui labels and sets calendar
        """
        # labels
        today = datetime.fromtimestamp(time.time())
        self.today_start.set_property('use-markup', True)
        self.today_start.set_label(
            '<small>Today: %s</small>' % today.strftime(self.format))
        self.today_end.set_property('use-markup', True)
        self.today_end.set_label(
            '<small>Today: %s</small>' % today.strftime(self.format))

        # calendars
        self.calendar_start.select_month(self.start_date.month-1,
            self.start_date.year)
        self.calendar_start.select_day(self.start_date.day)
        self.calendar_end.select_month(self.end_date.month-1,
            self.end_date.year)
        self.calendar_end.select_day(self.end_date.day)
    #end def init_calendars

    def gui_update(self):
        """
            This method is called when any changes are made and will
            calculate the difference between dates
        """
        (start_year, start_month, start_day) = self.calendar_start.get_date()
        (end_year, end_month, end_day) = self.calendar_end.get_date()

        # gtk calendar hack (months start with 0)
        self.start_date = date(start_year, start_month+1, start_day)
        self.end_date = date(end_year, end_month+1, end_day)

        self.recalulate_dates()

        self.entry_days.set_text(str(self.diff_days))
        self.entry_months.set_text(str(self.diff_months))
        self.entry_years.set_text(str(self.diff_years))
    #end def gui_update

    def recalulate_dates(self):
        """
            This method recalulates the difference between start and end dates
        """

        logger.debug('start_date : %s' % self.start_date)
        logger.debug('  end_date : %s' % self.end_date)

        self.entry_from.set_text(self.start_date.strftime(self.format))
        self.entry_to.set_text(self.end_date.strftime(self.format))

        self.entry_start.set_text(self.start_date.strftime(self.format))
        self.entry_end.set_text(self.end_date.strftime(self.format))

        diff_timedelta = self.end_date - self.start_date
        logger.debug('Days apart : %s', diff_timedelta.days)
        diff_days = diff_timedelta.days
        diff_years = self.end_date.year - self.start_date.year
        diff_months = self.end_date.month - self.start_date.month
        diff_months = diff_months + diff_years * 12

        #TODO: should we be using 'whole' years
        whole_years = 0
        if diff_months < 0:
            whole_years += 1
            whole_years += math.floor((diff_months-1)/12)
        else:
            whole_years += math.floor(diff_months/12)

        whole_months = 0
        if diff_months < 0:
            if (self.end_date.day > self.start_date.day):
                whole_months += 1
        else:
            if (self.end_date.day < self.start_date.day):
                whole_months -= 1

        whole_months += self.end_date.month - self.start_date.month
        whole_months = whole_months + whole_years * 12

        whole_years = math.floor(whole_months/12)

        logger.debug(
            'Difference -> years:%s months:%s days:%s whole_years:%s whole_months:%s',
            diff_years, diff_months, diff_days, whole_years, whole_months)

        self.diff_days = int(diff_days)
        self.diff_months = int(whole_months)
        self.diff_years = int(whole_years)
        logger.info('Difference -> years:%s months:%s days:%s',
            self.diff_years, self.diff_months, self.diff_days)
    #end def recalulate_dates

    #
    # gtk signals
    #
    def on_keyboard_interrupt(self):
        """
        This method is called by the default implementation of run()
        after a program is finished by pressing Control-C.
        """
        logger.info("Received KeyboardInterrupt ...")
        self.close_logger()
        pass
    #end def on_keyboard_interrupt

    def on_window_destroy(self, widget, data=None):
        self.quit()
    #end def on_window_destroy

    def on_calendar_start_day_selected(self, w):
        self.gui_update()
    #end def on_calendar_start_day_selected

    def on_calendar_end_day_selected(self, w):
        self.gui_update()
    #end def on_calendar_end_day_selected

    def on_eventbox_today_start_button_press_event(self, w, event):
        today = datetime.fromtimestamp(time.time())
        self.start_date  = today
        self.calendar_start.select_month(self.start_date.month-1,
            self.start_date.year)
        self.calendar_start.select_day(self.start_date.day)
    #end def on_today_start_button_press_event

    def on_eventbox_today_end_button_press_event(self, w, event):
        today = datetime.fromtimestamp(time.time())
        self.end_date  = today
        self.calendar_end.select_month(self.end_date.month-1,
            self.end_date.year)
        self.calendar_end.select_day(self.end_date.day)
    #end def on_today_end_button_press_event

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

