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

__version__ = '0.1.4'
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
    date_formats = [
        '%m/%d/%Y', '%m/%d/%y', '%b/%d/%Y', '%B/%d/%Y', '%b/%d/%y',
        '%Y/%m/%d', '%y/%m/%d', '%Y/%b/%d', '%Y/%B/%d', '%y/%b/%d',
        '%m-%d-%Y', '%m-%d-%y', '%b-%d-%Y', '%B-%d-%Y', '%b-%d-%y',
        '%Y-%m-%d', '%y-%m-%d', '%Y-%b-%d', '%Y-%B-%d', '%y-%b-%d']

    updating = False

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
                #logger.info(os.path.dirname(sys.argv[0]))
                # we are in the /resources subdirectory already
                main_ui = os.path.join(os.path.dirname(__file__), 'ui/main.ui')
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
                self.entry_start.connect('changed', self.on_entry_start_changed)

                self.entry_end = self.builder.get_object('entry_end')
                self.entry_end.connect('changed', self.on_entry_end_changed)

                self.entry_from = self.builder.get_object('entry_from')
                self.entry_to = self.builder.get_object('entry_to')


                self.entry_days = self.builder.get_object('entry_days')
                self.entry_months = self.builder.get_object('entry_months')
                self.entry_years = self.builder.get_object('entry_years')

                self.eventbox_swap_start = self.builder.get_object('eventbox_swap_start')
                self.eventbox_swap_start.connect('button-press-event', self.on_eventbox_swap_button_press_event)

                self.eventbox_swap_end = self.builder.get_object('eventbox_swap_end')
                self.eventbox_swap_end.connect('button-press-event', self.on_eventbox_swap_button_press_event)

                # add some tooltips
                today = datetime.fromtimestamp(time.time())

                tip = 'Enter date in %s format (%s)' % (self.format.replace('%', ''), today.strftime(self.format))
                self.entry_start.set_tooltip_text(tip)
                self.entry_end.set_tooltip_text(tip)

                tip = 'Click to swap start and end dates'
                self.eventbox_swap_start.set_tooltip_text(tip)
                self.eventbox_swap_end.set_tooltip_text(tip)

                tip = 'Click to set calendar date to today (%s)' % today.strftime(self.format)
                self.eventbox_today_start.set_tooltip_text(tip)
                self.eventbox_today_end.set_tooltip_text(tip)

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

            # set the default icon to the GTK "info" icon
            gtk.window_set_default_icon_name(gtk.STOCK_INFO)

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
            console_format += " (%(name)s:%(funcName)s)" # add module name
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
        logger.debug('Initializing date objects')
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
        logger.debug('Initializing gui elements')
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
        self.updating = False
    #end def init_calendars

    def gui_update(self, w=None):
        """
            This method is called when any changes are made and will
            calculate the difference between dates
        """
        if self.updating == True:
            # lets hold off until we finish updating all elements
            return

        try:
            self.updating = True
            change = False

            if not self.get_date_from_calendar(self.calendar_start) == self.start_date:
                self.calendar_start.select_month(self.start_date.month-1,
                    self.start_date.year)
                self.calendar_start.select_day(self.start_date.day)
                change = True
            if not self.get_date_from_calendar(self.calendar_end) == self.end_date:
                self.calendar_end.select_month(self.end_date.month-1,
                    self.end_date.year)
                self.calendar_end.select_day(self.end_date.day)
                change = True

            if not self.entry_start.get_text() == self.start_date.strftime(self.format):
                self.entry_start.set_text(self.start_date.strftime(self.format))
                change = True
            if not self.entry_end.get_text() == self.end_date.strftime(self.format):
                self.entry_end.set_text(self.end_date.strftime(self.format))
                change = True

            if change == True:
                self.entry_from.set_text(self.start_date.strftime(self.format))
                self.entry_to.set_text(self.end_date.strftime(self.format))

                # Ok we have changes, so lets recalculate the difference
                (self.diff_days, self.diff_months, self.diff_years) = self.calculate_diff(self.start_date, self.end_date)

                self.entry_days.set_text(str(self.diff_days))
                self.entry_months.set_text(str(self.diff_months))
                self.entry_years.set_text(str(self.diff_years))

        except Exception as (e):
            logger.error('%s' % str(e))
            self.updating = False

        self.updating = False
    #end def gui_update

    def get_dates(self):
        self.start_date = self.get_date_from_calendar(self.calendar_start)
        self.end_date   = self.get_date_from_calendar(self.calendar_end)
    #end def get_dates

    def get_date_from_calendar(self, calendar=None):
        import gtk
        if isinstance(calendar, gtk.Calendar):
            (year, month, day) = calendar.get_date()
            # gtk calendar hack (months start with 0)
            return date(year, month+1, day)
    #end def get_dates_from_calendar

    def calculate_diff(self, start_date, end_date):
        """
            This method calulates the difference between start and end dates
        """
        logger.info('Dates  -> [%s] <-> [%s]' % (start_date, end_date))
        diff_timedelta = end_date - start_date

        diff_years = end_date.year - start_date.year
        diff_months = end_date.month - start_date.month
        diff_days = end_date.day - start_date.day

        whole_years = 0
        whole_months = diff_months + diff_years * 12
        if end_date < start_date:
            # we have a negative timedelta
            if diff_days < 0:
                whole_months += 1
            if whole_months < 0:
                if diff_days > 0:
                    whole_months += 1
                whole_years = math.floor((whole_months-1)/12) + 1
            else:
                if diff_days < 0:
                    whole_months -= 1
                whole_years = math.floor((whole_months)/12)
        else:
            # we have a positive timedelta
            if diff_days < 0:
                whole_months -= 1
            whole_years = math.floor((whole_months)/12)

        whole_years = int(whole_years)
        whole_days  = int(diff_timedelta.days)
        logger.info('Difference -> days:%s months:%s years:%s',
            whole_days, whole_months, whole_years)
        return (whole_days, whole_months, whole_years)
    #end def calculate_diff

    def parse_date(self, text):
        """
            Attempts to return a vaild datetime from a string entry and
            returns None if unable to match.
        """
        try:
            dt = datetime.strptime(text, self.format)
        except:
            pass
        else:
            return date(dt.year, dt.month, dt.day)

        for f in self.date_formats:
            try:
                dt = datetime.strptime(text, f)
            except:
                pass
            else:
                return date(dt.year, dt.month, dt.day)
        return None
    #end def parse_date

    #
    # gtk signals
    #
    def log_caller(self):
        caller = sys._getframe(1)
        #parent = sys._getframe(2)
        #caller.f_code.co_filename caller.f_code.co_name
        logger.debug("action -> %s", caller.f_code.co_name)
    #end def log_caller

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
        self.log_caller()
        self.quit()
    #end def on_window_destroy

    def on_calendar_start_day_selected(self, w):
        self.log_caller()
        if not self.updating:
            self.get_dates()
            self.gui_update()
    #end def on_calendar_start_day_selected

    def on_calendar_end_day_selected(self, w):
        self.log_caller()
        if not self.updating:
            self.get_dates()
            self.gui_update()
    #end def on_calendar_end_day_selected

    def on_eventbox_today_start_button_press_event(self, w, event):
        self.log_caller()
        today = date.fromtimestamp(time.time())
        self.start_date  = today
        if not self.updating:
            self.gui_update()
    #end def on_today_start_button_press_event

    def on_eventbox_today_end_button_press_event(self, w, event):
        self.log_caller()
        today = date.fromtimestamp(time.time())
        self.end_date  = today
        if not self.updating:
            self.gui_update()
    #end def on_today_end_button_press_event

    def on_entry_start_changed(self, w):
        self.log_caller()
        date = self.parse_date(w.get_text())
        if date:
            self.start_date = date
            if not self.updating:
                self.gui_update()
    #end def on_entry_start_changed

    def on_entry_end_changed(self, w):
        self.log_caller()
        date = self.parse_date(w.get_text())
        if not date == None:
            self.end_date = date
            if not self.updating:
                self.gui_update()
    #end def on_entry_start_changed

    def on_eventbox_swap_button_press_event(self, w, event):
        self.log_caller()
        end_date = self.start_date
        start_date = self.end_date
        self.end_date = end_date
        self.start_date = start_date
        if not self.updating:
            self.gui_update()
    #end def def on_eventbox_swap_button_press_event


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

