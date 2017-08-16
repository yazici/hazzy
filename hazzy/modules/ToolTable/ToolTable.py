#!/usr/bin/env python

#   Copyright (c) 2017 Kurt Jacobson
#      <kurtcjacobson@gmail.com>
#
#   This file is part of Hazzy.
#
#   Hazzy is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Hazzy is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Hazzy.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

# Setup paths
PYDIR = os.path.abspath(os.path.dirname(__file__))
HAZZYDIR = os.path.abspath(os.path.join(PYDIR, '../../..'))
if HAZZYDIR not in sys.path:
    sys.path.insert(1, HAZZYDIR)

UIDIR = os.path.join(PYDIR, 'ui')

# Setup logging
from constants import Paths
from hazzy.utilities import logger
from hazzy.utilities.status import Status
from hazzy.utilities.entryeval import EntryEval
#from hazzy.utilities.getiniinfo import GetIniInfo

log = logger.get("HAZZY.TOOL_TABLE")


class ToolTable(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self)

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(UIDIR, 'ToolTable.ui'))
        self.builder.connect_signals(self)

        self.treeview = self.builder.get_object('treeview')
        self.toolbar = self.builder.get_object('toolbar')
        self.liststore = self.builder.get_object('tool_liststore')

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)

        box.pack_start(self.toolbar, True, False, 0)
        box.pack_start(self.treeview, True, False, 0)

        self.add(box)

        self.eval = EntryEval().eval

        self.tool_table = 'tool.tbl'
        self.use_touchpad = False



# =========================================================
# ToolTable handlers
# =========================================================

    # Parse and load tool table into the treeview
    # More or less copied from Chris Morley's GladeVcp tooledit widget
    def load_tool_table(self, fn = None):
        # If no valid tool table given
        if fn is None:
            fn = self.tool_table
        if not os.path.exists(fn):
            log.warning("Tool table does not exist")
            return
        self.liststore.clear()  # Clear any existing data
        log.debug("Loading tool table: {0}".format(fn))
        with open(fn, "r") as tf:
            tool_table = tf.readlines()

        self.toolinfo = []  # TODO move to __init__
        for line in tool_table:
            # Separate tool data from comments
            comment = ''
            index = line.find(";")  # Find comment start index
            if index == -1:  # Delimiter ';' is missing, so no comments
                line = line.rstrip("\n")
            else:
                comment = (line[index+1:]).rstrip("\n")
                line = line[0:index].rstrip()
            array = [False, 1, 1, '0', '0', comment, 'white']
            # search beginning of each word for keyword letters
            # offset 0 is the checkbox so ignore it
            # if i = ';' that is the comment and we have already added it
            # offset 1 and 2 are integers the rest floats
            for offset, i in enumerate(['S', 'T', 'P', 'D', 'Z', ';']):
                if offset == 0 or i == ';':
                    continue
                for word in line.split():
                    if word.startswith(i):
                        if offset in(1, 2):
                            try:
                                array[offset] = int(word.lstrip(i))
                            except ValueError:
                                msg = 'Error reading tool table, can\'t convert "{0}" to integer in {1}' \
                                    .format(word.lstrip(i), line)
                                log.error(msg)
                                # self._show_message(["ERROR", msg])
                        else:
                            try:
                                array[offset] = "%.4f" % float(word.lstrip(i))
                            except ValueError:
                                msg = 'Error reading tool table, can\'t convert "{0}" to float in {1}' \
                                    .format(word.lstrip(i), line)
                                log.error(msg)
                                # self._show_message(["ERROR", msg])
                        break

            # Add array to liststore
            self.add_tool(array)

    # Save tool table
    # More or less copied from Chris Morley's GladeVcp tooledit widget
    def save_tool_table(self, fn=None):
        if fn is None:
            fn = self.tool_table
        if fn is None:
            return
        log.debug("Saving tool table as: {0}".format(fn))
        fn = open(fn, "w")
        for row in self.liststore:
            values = [value for value in row]
            line = ""
            for num,i in enumerate(values):
                if num in (0, 6):
                    continue
                elif num in (1, 2):  # tool# pocket#
                    line = line + "%s%d " % (['S', 'T', 'P', 'D', 'Z', ';'][num], i)
                else:
                    line = line + "%s%s " % (['S', 'T', 'P', 'D', 'Z', ';'][num], i.strip())
            # Write line to file
            fn.write(line + "\n")
        # Theses lines make sure the OS doesn't cache the data so that
        # linuxcnc will actually load the updated tool table
        fn.flush()
        os.fsync(fn.fileno())
        linuxcnc.command().load_tool_table()

    def add_tool(self, data=None):
        self.liststore.append(data)

    def get_selected_tools(self):
        model = self.liststore
        tools = []
        for row in range(len(model)):
            if model[row][0] == 1:
                tools.append(int(model[row][1]))
        return tools

    def on_delete_selected_clicked(self, widget):
        model = self.liststore
        rows = []
        for row in range(len(model)):
            if model[row][0] == 1:
                rows.append(row)
        rows.reverse()  # So we don't invalidate iters
        for row in rows:
            model.remove(model.get_iter(row))

    def on_change_to_selected_tool_clicked(self, widget, data=None):
        selected = self.get_selected_tools()
        if len(selected) == 1:
            tool_num = selected[0]
            self.issue_mdi('M6 T{0} G43'.format(tool_num))
        else:
            num = len(selected)
            msg = "{0} tools selected, you must select exactly one".format(num)
            log.error(msg)
            # self._show_message(["ERROR", msg])

    def on_add_tool_clicked(self, widget, data=None):
        num = len(self.liststore) + 1
        array = [0, num, num, '0.0000', '0.0000', 'New Tool', 'white']
        self.add_tool(array)

    def on_load_tool_table_clicked(self, widget, data=None):
        self.load_tool_table()

    def on_save_tool_table_clicked(self, widget, data=None):
        self.save_tool_table()

    def on_tool_num_edited(self, widget, path, new_text):
        try:
            new_int = int(new_text)
            self.liststore[path][1] = new_int
            self.liststore[path][2] = new_int
        except ValueError:
            msg = '"{0}" is not a valid tool number'.format(new_text)
            log.error(msg)
            # self._show_message(["ERROR", msg])

    def on_tool_pocket_edited(self, widget, path, new_text):
        try:
            new_int = int(new_text)
            self.liststore[path][2] = new_int
        except ValueError:
            msg = '"{0}" is not a valid tool pocket'.format(new_text)
            log.error(msg)
            # self._show_message(["ERROR", msg])

    def on_tool_dia_edited(self, widget, path, new_text):
        try:
            num = self.eval(new_text)
            self.liststore[path][3] = "{:.4f}".format(float(num))
        except:
            msg = '"{0}" does not evaluate to a valid tool diameter'.format(new_text)
            log.error(msg)
            # self._show_message(["ERROR", msg])

    def on_z_offset_edited(self, widget, path, new_text):
        try:
            num = self.eval(new_text)
            self.liststore[path][4] = "{:.4f}".format(float(num))
        except:
            msg = '"{0}" does not evaluate to a valid tool length'.format(new_text)
            log.error(msg)
            # self._show_message(["ERROR", msg])

    def on_tool_remark_edited(self, widget, path, new_text):
        self.liststore[path][5] =  new_text

    # Popup int numpad on int edit
    def on_int_editing_started(self, renderer, entry, row):
        if self.use_touchpad:
            self.int_touchpad.show(entry)

    # Popup float numpad on float edit
    def on_float_editing_started(self, renderer, entry, row):
        if self.use_touchpad:
            self.float_touchpad.show(entry, self.machine_units)

    # Popup keyboard on text edit
    def on_remark_editing_started(self, renderer, entry, row):
        if self.use_touchpad:
            self.keyboard.show(entry)

    # Toggle selection checkbox value
    def on_select_toggled(self, widget, row):
        model = self.liststore
        model[row][0] = not model[row][0]

    # For single click selection and edit
    def on_treeview_button_press_event(self, widget, event):
        if event.button == 1:  # left click
            try:
                row, col, x, y = widget.get_path_at_pos(int(event.x), int(event.y))
                widget.set_cursor(row, None, True)
            except:
                pass

    # Used for indicating tool in spindle
    def highlight_tool(self, tool_num):
        model = self.liststore
        for row in range(len(model)):
            model[row][0] = 0
            model[row][6] = "white"
            if model[row][1] == tool_num:
                self.current_tool_data = model[row]
                model[row][6] = "gray"

    # This is not used now, but might be useful at some point
    def set_selected_tool(self, toolnum):
        model = self.liststore
        found = False
        for row in range(len(model)):
            if model[row][1] == toolnum:
                found = True
                break
        if found:
            model[row][0] = 1 # Check the box
            self.widgets.tooltable_treeview.set_cursor(row)
        else:
            log.warning("Did not find tool {0} in the tool table".format(toolnum))


def main():
    Gtk.main()

if __name__ == '__main__':
    win = Gtk.Window()
    win.connect('destroy', Gtk.main_quit)
    tt = ToolTable()
    tt.load_tool_table(tt.tool_table)
    win.add(tt)
    win.show_all()
    main()