#!/usr/bin/env python3
import os
import subprocess
import gi.repository
gi.require_version('Budgie', '1.0')
from gi.repository import Budgie, GObject, Gtk

userhome = os.environ["HOME"]


# config path
dr = os.path.join(userhome, ".config", "budgie-extras", "folderjumper")
# settings files
showinvisible = os.path.join(dr, "showinvisible")
hidetooltips = os.path.join(dr, "hidetooltips")
defdirfile = os.path.join(dr, "defaultdir")


# tooltips
tooltip1 = "Left-click to open file, right-click to open its directory"
tooltip2 = "Right-click to open"


try:
    os.makedirs(dr)
except FileExistsError:
    pass


def get_defaultdir():
    try:
        return open(defdirfile).read().strip()
    except FileNotFoundError:
        return userhome


class Kangaroo(GObject.GObject, Budgie.Plugin):

    __gtype_name__ = "Kangaroo"

    def __int__(self):
        GObject.Object.__init__(self)

    def do_get_panel_widget(self, uuid):
        return KangarooApplet(uuid)


class KangarooSettings(Gtk.Grid):

    def __init__(self, setting):

        super().__init__()

        self.setting = setting
        # grid & layout
        self.set_row_spacing(12)
        self.hidetooltips = Gtk.CheckButton("Hide tooltips")
        self.showinvisibles = Gtk.CheckButton("Show hidden files")
        element_hsizer1 = self.h_spacer(13)
        self.set_root = Gtk.Button("Set root directory")
        self.set_root.connect("clicked", self.get_directory)
        self.dir_entry = Gtk.Entry(editable=False)
        self.dir_entry.set_text(get_defaultdir())
        self.hidetooltips.set_active(os.path.exists(hidetooltips))
        self.showinvisibles.set_active(os.path.exists(showinvisible))
        self.hidetooltips.connect(
            "toggled", self.edit_settings, hidetooltips
        )
        self.showinvisibles.connect(
            "toggled", self.edit_settings, showinvisible
        )
        self.attach(self.hidetooltips, 1, 1, 1, 1)
        self.attach(self.showinvisibles, 1, 2, 1, 1)
        self.attach(element_hsizer1, 1, 3, 1, 1)
        self.attach(self.set_root, 1, 4, 1, 1)
        self.attach(self.dir_entry, 1, 5, 1, 1)
        self.show_all()

    def h_spacer(self, addwidth):
        # horizontal spacer
        spacegrid = Gtk.Grid()
        if addwidth:
            label1 = Gtk.Label()
            label2 = Gtk.Label()
            spacegrid.attach(label1, 0, 0, 1, 1)
            spacegrid.attach(label2, 0, 1, 1, 1)
            spacegrid.set_row_spacing(addwidth)
        return spacegrid

    def get_directory(self, button):
        try:
            directory = subprocess.check_output([
                "zenity", "--file-selection", "--directory",
            ]).decode("utf-8").strip()
        except subprocess.CalledProcessError:
            pass
        else:
            self.dir_entry.set_text(directory)
            open(defdirfile, "wt").write(directory)

    def edit_settings(self, button, settingsfile):
        state = button.get_active()
        if state:
            open(settingsfile, "wt").write("")
        else:
            try:
                os.remove(settingsfile)
            except FileNotFoundError:
                pass


class KangarooApplet(Budgie.Applet):

    manager = None

    def __init__(self, uuid):

        Budgie.Applet.__init__(self)
        self.uuid = uuid
        self.menu = Gtk.Menu()

        """
        unfortunately, if a menuitem has a submenu, it won't act on righ / left
        button press, connected to the menuitem. we therefore need to set the
        action globally for the menu as a whole. the downside is that (in this
        case)right- click still works on the last selected item if used outside
        the menu. no solution found. more a cosmetic issue than a use issue
        though. normally, most users will never notice. nevertheless, still
        looking for a solution.
        """

        self.menu.connect("button-press-event", self.open_onthree)
        box = Gtk.EventBox()
        self.add(box)
        icon = Gtk.Image.new_from_icon_name(
            "foldertrack-symbolic", Gtk.IconSize.MENU
        )
        box.add(icon)
        box.show_all()
        box.connect("button-press-event", self.popup_menu)
        self.fileselect = False
        self.currselectedfile = None
        self.show_all()
        self.menu.show_all()

    def popup_menu(self, *args):
        # refresh menu content on popup
        self.default_dir = get_defaultdir()
        for i in self.menu.get_children():
            self.menu.remove(i)
        self.hide_tooltips = os.path.exists(hidetooltips)
        self.show_invisibles = os.path.exists(showinvisible)
        self.create_level(self.default_dir, self.menu)
        self.show_all()
        self.menu.show_all()
        self.menu.popup(
            None, None, None, None, 0, Gtk.get_current_event_time()
        )

    def check_invisible(self, flist):
        # filter out invisoble files if set
        if not self.show_invisibles:
            return [
                f for f in flist if all([
                    not f.startswith("."), not f.endswith("~")
                ])
            ]
        else:
            return flist

    def tooltip(self, item, text):
        # set tooltip
        item.set_tooltip_text(text)

    def create_level(self, dr, master=None, *args):
        # create new menu layer items
        newitems = sorted(self.check_invisible(os.listdir(dr)))
        # show "Empty" on empty folders. should show a > nevertheless
        if not newitems:
            firstsub = Gtk.MenuItem("Empty")
            master.append(firstsub)
        # if not empty, show content on select / activate
        else:
            for item in newitems:
                # item, firstsub
                firstsub = Gtk.MenuItem(item)
                master.append(firstsub)
                newpath = os.path.join(dr, item)
                try:
                    secondsubitems = self.check_invisible(
                        os.listdir(newpath)
                    )
                except NotADirectoryError:
                    self.dressup_filemenuitem(firstsub, item, newpath)
                except PermissionError:
                    pass
                else:
                    self.dressup_dirmenuitem(firstsub, item, newpath)

    def dressup_filemenuitem(self, menuitem, itemname, newpath):
        # setup the file- menuitem
        menuitem.set_label("•    " + itemname)
        menuitem.connect(
            "button-press-event", self.open_file_onone, newpath
        )
        if not self.hide_tooltips:
            self.tooltip(menuitem, tooltip1)
        menuitem.connect(
            "select", self.get_selectedfile, True, newpath
        )

    def dressup_dirmenuitem(self, menuitem, itemname, newpath):
        # setup the directory- menuitem
        secondsub = Gtk.Menu()
        menuitem.set_submenu(secondsub)
        menuitem.connect("activate", self.add_layer, newpath)
        menuitem.connect(
            "select", self.get_selectedfile, False, newpath
        )
        menuitem.set_label("⏍ " + itemname)
        if not self.hide_tooltips:
            self.tooltip(menuitem, tooltip2)

    def add_layer(self, menuitem, newpath):
        # initiate a new, deeper layer
        newmenu = Gtk.Menu()
        menuitem.set_submenu(newmenu)
        self.create_level(newpath, newmenu)
        self.curr_subject = newpath
        menuitem.show_all()

    def get_selectedfile(self, widget, val, newpath):
        # get the currently selected file if applicable
        # sets False if latest selected is a dir
        self.fileselect = val
        self.currselectedfile = newpath

    def open_file_onone(self, menuitem, button, path):
        # open the selected file on left click
        if button.button == 1:
            self.curr_subject = path
            subprocess.Popen(["xdg-open", self.curr_subject])

    def open_onthree(self, event, button):
        # opens either the directory, if selected,
        # or the superior directory of a file, if selected
        if button.button == 3:
            if self.fileselect is False:
                path = self.curr_subject
            else:
                path = self.currselectedfile[
                    :self.currselectedfile.rfind("/")
                ]
            subprocess.Popen(["xdg-open", path])
            self.menu.popdown()

    def do_get_settings_ui(self):
        """Return the applet settings with given uuid"""
        return KangarooSettings(self.get_applet_settings(self.uuid))

    def do_supports_settings(self):
        """Return True if support setting through Budgie Setting,
        False otherwise.
        """
        return True
