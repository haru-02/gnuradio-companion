"""
Copyright 2008, 2009 Free Software Foundation, Inc.
This file is part of GNU Radio

GNU Radio Companion is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

GNU Radio Companion is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
"""

from __future__ import absolute_import
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

import sys
from distutils.spawn import find_executable

from . import Utils, Actions, Constants
from ..core import Messages


class SimpleTextDisplay(Gtk.TextView):
    """A non editable gtk text view."""

    def __init__(self, text=''):
        """
        TextDisplay constructor.

        Args:
            text: the text to display (string)
        """
        text_buffer = Gtk.TextBuffer()
        text_buffer.set_text(text)
        self.set_text = text_buffer.set_text
        GObject.GObject.__init__(self)
        self.set_editable(False)
        self.set_cursor_visible(False)
        self.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)


class TextDisplay(SimpleTextDisplay):

    def __init__(self, text=''):
        """
        TextDisplay constructor.

        Args:
            text: the text to display (string)
        """
        SimpleTextDisplay.__init__(self, text)
        self.scroll_lock = True
        self.connect("populate-popup", self.populate_popup)

    def insert(self, line):
        # make backspaces work
        line = self._consume_backspaces(line)
        # add the remaining text to buffer
        self.get_buffer().insert(self.get_buffer().get_end_iter(), line)
        # Automatically scroll on insert
        self.scroll_to_end()

    def _consume_backspaces(self, line):
        """removes text from the buffer if line starts with \b*"""
        if not line: return
        # for each \b delete one char from the buffer
        back_count = 0
        start_iter = self.get_buffer().get_end_iter()
        while line[back_count] == '\b':
            # stop at the beginning of a line
            if not start_iter.starts_line(): start_iter.backward_char()
            back_count += 1
        # remove chars
        self.get_buffer().delete(start_iter, self.get_buffer().get_end_iter())
        # return remaining text
        return line[back_count:]

    def scroll_to_end(self):
        if self.scroll_lock:
            buffer = self.get_buffer()
            buffer.move_mark(buffer.get_insert(), buffer.get_end_iter())
            # TODO: Fix later
            #self.scroll_to_mark(buffer.get_insert(), 0.0)

    def clear(self):
        buffer = self.get_buffer()
        buffer.delete(buffer.get_start_iter(), buffer.get_end_iter())

    def save(self, file_path):
        console_file = open(file_path, 'w')
        buffer = self.get_buffer()
        console_file.write(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))
        console_file.close()

    # Callback functions to handle the scrolling lock and clear context menus options
    # Action functions are set by the ActionHandler's init function
    def clear_cb(self, menu_item, web_view):
        Actions.CLEAR_CONSOLE()

    def scroll_back_cb(self, menu_item, web_view):
        Actions.TOGGLE_SCROLL_LOCK()

    def save_cb(self, menu_item, web_view):
        Actions.SAVE_CONSOLE()

    def populate_popup(self, view, menu):
        """Create a popup menu for the scroll lock and clear functions"""
        menu.append(Gtk.SeparatorMenuItem())

        lock = Gtk.CheckMenuItem("Scroll Lock")
        menu.append(lock)
        lock.set_active(self.scroll_lock)
        lock.connect('activate', self.scroll_back_cb, view)

        save = Gtk.ImageMenuItem(Gtk.STOCK_SAVE)
        menu.append(save)
        save.connect('activate', self.save_cb, view)

        clear = Gtk.ImageMenuItem(Gtk.STOCK_CLEAR)
        menu.append(clear)
        clear.connect('activate', self.clear_cb, view)
        menu.show_all()
        return False


def MessageDialogHelper(type, buttons, title=None, markup=None, default_response=None, extra_buttons=None):
    """
    Create a modal message dialog and run it.

    Args:
        type: the type of message: Gtk.MessageType.INFO, Gtk.MessageType.WARNING, Gtk.MessageType.QUESTION or Gtk.MessageType.ERROR
        buttons: the predefined set of buttons to use:
        Gtk.ButtonsType.NONE, Gtk.ButtonsType.OK, Gtk.ButtonsType.CLOSE, Gtk.ButtonsType.CANCEL, Gtk.ButtonsType.YES_NO, Gtk.ButtonsType.OK_CANCEL

    Args:
        title: the title of the window (string)
        markup: the message text with pango markup
        default_response: if set, determines which button is highlighted by default
        extra_buttons: a tuple containing pairs of values; each value is the button's text and the button's return value

    Returns:
        the gtk response from run()
    """
    message_dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, type, buttons)
    if title: message_dialog.set_title(title)
    if markup: message_dialog.set_markup(markup)
    if extra_buttons: message_dialog.add_buttons(*extra_buttons)
    if default_response: message_dialog.set_default_response(default_response)
    response = message_dialog.run()
    message_dialog.destroy()
    return response


def ErrorsDialog(flowgraph):
    MessageDialogHelper(
        type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CLOSE,
        title='Flow Graph Errors',
        markup='\n\n'.join(
            '<b>Error {num}:</b>\n{msg}'.format(num=i, msg=Utils.encode(msg.replace('\t', '  ')))
            for i, msg in enumerate(flowgraph.get_error_messages())
        ),
    )


class AboutDialog(Gtk.AboutDialog):
    """A cute little about dialog."""

    def __init__(self, config):
        """AboutDialog constructor."""
        GObject.GObject.__init__(self)
        self.set_name(config.name)
        self.set_version(config.version)
        self.set_license(config.license)
        self.set_copyright(config.license.splitlines()[0])
        self.set_website(config.website)
        self.run()
        self.destroy()


def HelpDialog(): MessageDialogHelper(
    type=Gtk.MessageType.INFO,
    buttons=Gtk.ButtonsType.CLOSE,
    title='Help',
    markup="""\
<b>Usage Tips</b>

<u>Add block</u>: drag and drop or double click a block in the block selection window.
<u>Rotate block</u>: Select a block, press left/right on the keyboard.
<u>Change type</u>: Select a block, press up/down on the keyboard.
<u>Edit parameters</u>: double click on a block in the flow graph.
<u>Make connection</u>: click on the source port of one block, then click on the sink port of another block.
<u>Remove connection</u>: select the connection and press delete, or drag the connection.

* See the menu for other keyboard shortcuts.""")


def TypesDialog(platform):
    colors = [(name, color) for name, key, sizeof, color in Constants.CORE_TYPES]
    max_len = 10 + max(len(name) for name, code in colors)

    message = '\n'.join(
        '<span background="{color}"><tt>{name}</tt></span>'
        ''.format(color=color, name=Utils.encode(name).center(max_len))
        for name, color in colors
    )
    MessageDialogHelper(
        type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.CLOSE,
        title='Types - Color Mapping',
        markup=message
    )


def MissingXTermDialog(xterm):
    MessageDialogHelper(
        type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.OK,
        title='Warning: missing xterm executable',
        markup=("The xterm executable {0!r} is missing.\n\n"
                "You can change this setting in your gnuradio.conf, in "
                "section [grc], 'xterm_executable'.\n"
                "\n"
                "(This message is shown only once)").format(xterm)
    )


def ChooseEditorDialog(config):
    # Give the option to either choose an editor or use the default
    # Always return true/false so the caller knows it was successful
    buttons = (
        'Choose Editor', Gtk.ResponseType.YES,
        'Use Default', Gtk.ResponseType.NO,
        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL
    )
    response = MessageDialogHelper(
        Gtk.MessageType.QUESTION, Gtk.ButtonsType.NONE, 'Choose Editor',
        'Would you like to choose the editor to use?', Gtk.ResponseType.YES, buttons
    )

    # Handle the inital default/choose/cancel response
    # User wants to choose the editor to use
    if response == Gtk.ResponseType.YES:
        file_dialog = Gtk.FileChooserDialog(
            'Select an Editor...', None,
            Gtk.FileChooserAction.OPEN,
            ('gtk-cancel', Gtk.ResponseType.CANCEL, 'gtk-open', Gtk.ResponseType.OK)
        )
        file_dialog.set_select_multiple(False)
        file_dialog.set_local_only(True)
        file_dialog.set_current_folder('/usr/bin')
        try:
            if file_dialog.run() == Gtk.ResponseType.OK:
                config.editor = file_path = file_dialog.get_filename()
                file_dialog.destroy()
                return file_path
        finally:
            file_dialog.destroy()

    # Go with the default editor
    elif response == Gtk.ResponseType.NO:
        # Determine the platform
        try:
            process = None
            if sys.platform.startswith('linux'):
                process = find_executable('xdg-open')
            elif sys.platform.startswith('darwin'):
                process = find_executable('open')
            if process is None:
                raise ValueError("Can't find default editor executable")
            # Save
            config.editor = process
            return process
        except Exception:
            Messages.send('>>> Unable to load the default editor. Please choose an editor.\n')
            # Just reset of the constant and force the user to select an editor the next time
            config.editor = ''
            return

    Messages.send('>>> No editor selected.\n')
    return
