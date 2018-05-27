import gi.repository
gi.require_version('Budgie', '1.0')
from gi.repository import Budgie, GObject, Gtk, Gio, Pango
import os
import weathertools as wt
import getweather as gw
import time
import subprocess


"""
Budgie WeatherShow
Author: Jacob Vlijm
Copyright © 2017-2018 Ubuntu Budgie Developers
Website=https://ubuntubudgie.org
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or any later version. This
program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details. You
should have received a copy of the GNU General Public License along with this
program.  If not, see <http://www.gnu.org/licenses/>.
"""


langlist = [
    'Arabic', 'Bulgarian', 'Catalan', 'Czech', 'German', 'Greek', 'English',
    'Persian (Farsi)', 'Finnish', 'French', 'Galician', 'Croatian',
    'Hungarian', 'Italian', 'Japanese', 'Korean', 'Latvian', 'Lithuanian',
    'Macedonian', 'Dutch', 'Polish', 'Portuguese', 'Romanian', 'Russian',
    'Swedish', 'Slovak', 'Slovenian', 'Spanish', 'Turkish', 'Ukrainian',
    'Vietnamese', 'Chinese Simplified', 'Chinese Traditional'
]


langcodes = [
    'ar', 'bg', 'ca', 'cz', 'de', 'el', 'en', 'fa', 'fi', 'fr', 'gl', 'hr',
    'hu', 'it', 'ja', 'kr', 'la', 'lt', 'mk', 'nl', 'pl', 'pt', 'ro', 'ru',
    'se', 'sk', 'sl', 'es', 'tr', 'ua', 'vi', 'zh_cn', 'zh_tw'
]


css_data = """
.colorbutton {
  border-color: transparent;
  background-color: hexcolor;
  padding: 0px;
  border-width: 1px;
  border-radius: 4px;
}
.colorbutton:hover {
  border-color: hexcolor;
  background-color: hexcolor;
  padding: 0px;
  border-width: 1px;
  border-radius: 4px;
}
"""


searchmsg = """Add two or more characters to the text field,
then press this button.
"""


colorpicker = os.path.join(wt.app_path, "colorpicker")
cpos_file = wt.pos_file
transparency = wt.transparency
currcity = wt.currcity
currlang = wt.currlang


# lists
w_icons = wt.w_icons
small_icons = wt.small_icons
markers = wt.markers
arrows = wt.arrows


class BudgieWeatherShow(GObject.GObject, Budgie.Plugin):
    """ This is simply an entry point into your Budgie Applet implementation.
        Note you must always override Object, and implement Plugin.
    """

    # Good manners, make sure we have unique name in GObject type system
    __gtype_name__ = "BudgieWeatherShow"

    def __init__(self):
        """ Initialisation is important.
        """
        GObject.Object.__init__(self)

    def do_get_panel_widget(self, uuid):
        """ This is where the real fun happens. Return a new Budgie.Applet
            instance with the given UUID. The UUID is determined by the
            BudgiePanelManager, and is used for lifetime tracking.
        """
        return BudgieWeatherShowApplet(uuid)


class BudgieWeatherShowSettings(Gtk.Grid):
    def __init__(self, setting):

        super().__init__()
        self.setting = setting
        # files & colors
        self.tcolorfile = wt.textcolor
        # city entry
        citylabel = Gtk.Label("City", xalign=0)
        self.attach(citylabel, 1, 1, 1, 1)
        self.citybox = Gtk.Box()
        self.cityentry = Gtk.Entry()
        try:
            c_string = wt.getcity()[1].strip()
        except TypeError:
            pass
        else:
            self.cityentry.set_text(c_string)
        self.citybox.pack_start(self.cityentry, False, False, 0)
        self.search_button = Gtk.MenuButton()
        self.citybox.pack_end(self.search_button, False, False, 0)
        self.icon1 = Gtk.Image.new_from_icon_name(
            "system-search-symbolic", Gtk.IconSize.DND)
        self.search_button.set_image(self.icon1)
        self.cityentry.connect("changed", self.update_citylist)
        self.attach(self.citybox, 1, 2, 1, 1)
        # city lookup
        self.citymenu = Gtk.Menu()
        menutitem = Gtk.MenuItem(searchmsg)
        self.citymenu.append(menutitem)
        self.citymenu.show_all()
        self.search_button.set_popup(self.citymenu)
        # space
        space2 = Gtk.Label("\n")
        self.attach(space2, 1, 6, 1, 1)
        # language
        self.lang_liststore = Gtk.ListStore(str)
        for lang in langlist:
            self.lang_liststore.append([lang])
        self.completion = Gtk.EntryCompletion()
        self.completion.set_model(self.lang_liststore)
        self.completion.set_text_column(0)
        self.langlabel = Gtk.Label("Language", xalign=0)
        self.attach(self.langlabel, 1, 7, 1, 1)
        self.langentry = Gtk.Entry()
        self.langentry.set_text(
            langlist[langcodes.index(wt.get_currlang())]
        )
        self.langentry.set_completion(self.completion)
        self.completion.connect("match-selected", self.apply_lang)
        self.attach(self.langentry, 1, 8, 1, 1)
        # space
        space3 = Gtk.Label("\n")
        self.attach(space3, 1, 9, 1, 1)
        # text color
        self.bholder1 = Gtk.Box()
        self.attach(self.bholder1, 1, 10, 1, 1)
        self.text_color = Gtk.Button()
        self.text_color.connect("clicked", self.pick_color, self.tcolorfile)
        self.text_color.set_size_request(10, 10)
        self.bholder1.pack_start(self.text_color, False, False, 0)
        textcolorlabel = Gtk.Label("  Set text color")
        self.bholder1.pack_start(textcolorlabel, False, False, 0)
        # space
        space4 = Gtk.Label("\n")
        self.attach(space4, 1, 11, 1, 1)
        # transparency
        curr_trans = int(float(wt.get_transparency()) * 100)
        transp_label = Gtk.Label("Background %", xalign=0)
        self.attach(transp_label, 1, 12, 1, 1)
        self.transp_slider = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 5
        )
        self.transp_slider.set_value(curr_trans)
        self.attach(self.transp_slider, 1, 13, 1, 1)
        self.transp_slider.connect("value_changed", self.update_transparency)
        # space
        space5 = Gtk.Label("\n")
        self.attach(space5, 1, 14, 1, 1)
        # checkbox custom position
        self.setposbutton = Gtk.CheckButton("Set custom position (px)")
        self.attach(self.setposbutton, 1, 15, 1, 1)
        # position
        posholder = Gtk.Box()
        self.xpos = Gtk.Entry()
        self.xpos.set_width_chars(4)
        self.xpos_label = Gtk.Label("x: ")
        self.ypos = Gtk.Entry()
        self.ypos.set_width_chars(4)
        self.ypos_label = Gtk.Label(" y: ")
        for item in [
            self.xpos_label, self.xpos, self.ypos_label, self.ypos,
        ]:
            posholder.pack_start(item, False, False, 0)
        self.apply = Gtk.Button("OK")
        self.apply.connect("pressed", self.get_xy)
        posholder.pack_end(self.apply, False, False, 0)
        self.attach(posholder, 1, 16, 1, 1)
        # space
        space6 = Gtk.Label(" ")
        self.attach(space6, 1, 17, 1, 1)
        # color buttons & labels
        self.set_initialstate()
        self.setposbutton.connect("toggled", self.toggle_cuspos)
        self.update_color()
        self.show_all()

    def update_transparency(self, slider):
        newval = str(int(self.transp_slider.get_value()) / 100)
        wt.write_settings(transparency, newval)
        wt.restart_weather()

    def apply_lang(self, widget, ls, tr):
        newlang = ls[tr][self.completion.get_text_column()]
        langcode = langcodes[langlist.index(newlang)]
        open(currlang, "wt").write(langcode)
        wt.restart_weather()

    def apply_selection(self, menu, selection, citycode):
        self.cityentry.set_text(selection)
        open(currcity, "wt").write("\n".join([citycode, selection]))
        wt.restart_weather()

    def update_citylist(self, widget):
        # it turns out also city data can be downloaded as json :)
        # Change functions here and in tools? <- no, leave it.
        currprint = self.cityentry.get_text()
        for item in self.citymenu.get_children():
            item.destroy()
        if len(currprint) >= 2:
            newdata = wt.get_citymatches(currprint)
            newselection = newdata[0]
            if not newdata[1]:
                subprocess.Popen([
                    "notify-send", "-i", "budgie-wticon-symbolic", "Wooops",
                    "Connection error: please check your internet connection"
                ])
            for c in newselection:
                add = c.split()
                newcity = " ".join(add[1:-3]) + ", " + add[-1]
                code = add[0]
                newmenuitem = Gtk.MenuItem(newcity)
                self.citymenu.append(newmenuitem)
                newmenuitem.connect(
                    "activate", self.apply_selection, newcity, code
                )
        self.citymenu.show_all()
        self.search_button.set_popup(self.citymenu)
        self.show_all()

    def set_initialstate(self):
        # set initial state of items in the custom position section
        state_data = wt.get_position()
        state = state_data[0]
        if state:
            self.xpos.set_text(str(state_data[1]))
            self.ypos.set_text(str(state_data[2]))
        for entr in [
            self.ypos, self.xpos, self.apply, self.xpos_label, self.ypos_label
        ]:
            entr.set_sensitive(state)
        self.setposbutton.set_active(state)

    def get_xy(self, button):
        x = self.xpos.get_text()
        y = self.ypos.get_text()
        # check for correct input
        try:
            newpos = [str(int(p)) for p in [x, y]]
            open(cpos_file, "wt").write("\n".join(newpos))
        except (FileNotFoundError, ValueError, IndexError):
            pass
        wt.restart_weather()

    def toggle_cuspos(self, button):
        newstate = button.get_active()
        for widget in [
            self.ypos, self.xpos, self.xpos_label, self.ypos_label, self.apply
        ]:
            widget.set_sensitive(newstate)
        if newstate is False:
            self.xpos.set_text("")
            self.ypos.set_text("")
            try:
                os.remove(cpos_file)
            except FileNotFoundError:
                pass
            else:
                wt.restart_weather()

    def h_spacer(self, addwidth):
        # horizontal spacer
        spacegrid = Gtk.Grid()
        if addwidth:
            label1 = Gtk.Label()
            label2 = Gtk.Label()
            spacegrid.attach(label1, 0, 0, 1, 1)
            spacegrid.attach(label2, 1, 0, 1, 1)
            spacegrid.set_column_spacing(addwidth)
        return spacegrid

    def set_css(self, hexcol):
        provider = Gtk.CssProvider.new()
        provider.load_from_data(
            css_data.replace("hexcolor", hexcol).encode()
        )
        return provider

    def color_button(self, button, hexcol):
        provider = self.set_css(hexcol)
        color_cont = button.get_style_context()
        color_cont.add_class("colorbutton")
        Gtk.StyleContext.add_provider(
            color_cont,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def update_color(self, *args):
        self.tcolor = wt.hexcolor(wt.read_color(self.tcolorfile))
        self.color_button(self.text_color, self.tcolor)

    def pick_color(self, button, f):
        wdata = wt.get(["wmctrl", "-l"])
        if "WeatherShow - set color" not in wdata:
            subprocess = Gio.Subprocess.new([colorpicker, f], 0)
            subprocess.wait_check_async(None, self.update_color)
            self.update_color()


class BudgieWeatherShowApplet(Budgie.Applet):
    """ Budgie.Applet is in fact a Gtk.Bin """

    def __init__(self, uuid):
        Budgie.Applet.__init__(self)
        self.uuid = uuid
        self.box = Gtk.EventBox()
        icon = Gtk.Image.new_from_icon_name(
            "budgie-wticon-symbolic", Gtk.IconSize.MENU,
        )
        self.box.add(icon)
        self.add(self.box)
        self.box.show_all()
        self.show_all()
        # add grid stuff
        self.popupgrid = Gtk.Grid()
        # menu
        self.popover = Budgie.Popover.new(self.box)
        self.popover.add(self.popupgrid)
        self.popover.get_child().show_all()
        self.box.connect("button-press-event", self.on_press)
        wt.restart_weather()

    def on_press(self, box, arg):
        self.run_update()
        self.manager.show_popover(self.box)

    def do_update_popovers(self, manager):
        self.manager = manager
        self.manager.register_popover(self.box, self.popover)

    def get_multiday(self, key, city, lang):
        try:
            all_data = gw.get_data(key, city, "forecast", lang)["list"]
        except (TypeError, KeyError):
            all_data = None
        if all_data:
            today = {}
            forecast = {}
            for snapshot in all_data:
                try:
                    # get snapshot time
                    t = snapshot["dt_txt"]
                except KeyError:
                    pass
                else:
                    currdate = time.strftime("%Y-%m-%d")
                    if t.startswith(currdate):
                        today[t] = gw.check_dictpaths(snapshot)
                    elif t.endswith("15:00:00"):
                        forecast[t] = gw.check_dictpaths(snapshot)
            return {"today": today, "forecast": forecast}

    def h_spacer(self, addwidth):
        spacegrid = Gtk.Grid()
        if addwidth:
            label1 = Gtk.Label()
            label2 = Gtk.Label()
            spacegrid.attach(label1, 0, 0, 1, 1)
            spacegrid.attach(label2, 1, 0, 1, 1)
            spacegrid.set_column_spacing(addwidth)
        return spacegrid

    def add_timelabel(self, src, t, x, y, spx, spy):
        # time/day section header
        showtime_src = t.split()[1]
        showtime = showtime_src[:showtime_src.rfind(":")]
        showtime_label = Gtk.Label(showtime)
        showtime_label.modify_font(Pango.FontDescription(self.font + " bold"))
        self.popupgrid.attach(showtime_label, x, y, spx, spy)

    def add_daylabel(self, d, x, y, spx, spy):
        dayname = wt.get_dayname(d.split()[0])
        dayname_label = Gtk.Label(dayname)
        dayname_label.modify_font(Pango.FontDescription(self.font + " bold"))
        self.popupgrid.attach(dayname_label, x, y, 1, 1)

    def add_icon(self, src, x, y, spx, spy):
        image = Gtk.Image()
        self.popupgrid.attach(image, x, y, spx, spy)
        td_icon = src["icon"]  # <- exists by definition, but can be None
        if td_icon:
            index = markers.index(td_icon)
            self.set_smallicon(image, index)

    def prepare_windlabel(self, src):
        newdeg = src["wind_deg"]
        newdeg = arrows[round(newdeg / 45)] if newdeg else ""
        newspeed = src["wind_speed"]
        speed_mention = str(newspeed) + " m/s" if newspeed else ""
        return " ".join([newdeg, speed_mention])

    def run_update(self):
        for c in self.popupgrid.get_children():
            c.destroy()
        self.font = wt.get_font()
        # rows 0-1
        # space top left / bottom right
        self.popupgrid.attach(Gtk.Label("\t"), 0, 0, 1, 1)
        self.popupgrid.attach(Gtk.Label("\n\t"), 100, 100, 1, 1)
        # Today header, only show if any items in today section
        # (not around 24:00)
        self.today_label = Gtk.Label("Today", xalign=0.5)
        self.today_label.modify_font(Pango.FontDescription(self.font + " 16"))
        # forecast header
        self.forecast_label = Gtk.Label("\nForecast\n", xalign=0.5)
        self.forecast_label.modify_font(
            Pango.FontDescription(self.font + " 16")
        )
        self.popupgrid.attach(self.forecast_label, 1, 20, 100, 1)
        # get data
        key = wt.getkey()
        city = str(wt.getcity()[0]).strip()
        lang = wt.get_currlang()
        wdata = self.get_multiday(key, city, lang)
        try:
            today = wdata["today"]
        except TypeError:
            # fill popupgrid with message
            nodatalabel = Gtk.Label("\nWooops, no data available\t")
            nodatalabel.modify_font(Pango.FontDescription(self.font + " 26"))
            self.popupgrid.attach(nodatalabel, 1, 6, 100, 1)
        else:
            times = sorted([k for k in today.keys()])
            self.update_today(today, times)
        try:
            forec = wdata["forecast"]
        except TypeError:
            pass
        else:
            days = sorted([k for k in forec.keys()])
            self.update_forecast(forec, days)
        self.popupgrid.show_all()
        self.show_all()

    def update_today(self, today, times):
        # topleft position in grid
        n1 = 1  # today start (x)
        if times:
            self.popupgrid.attach(self.today_label, 1, 1, 100, 1)
        for t in times:
            # section start (y)
            n2 = 5
            src = today[t]
            # set width
            self.popupgrid.attach(self.h_spacer(120), n1, n2, 1, 1)
            # get today's data, time label
            self.add_timelabel(src, t, n1, n2 + 1, 1, 1)
            # icon
            self.add_icon(src, n1, n2 + 2, 1, 1)
            # prepare wind display
            windmention = self.prepare_windlabel(src)
            # fill in the easy ones
            for item in [
                wt.validate_val(src["sky"]),
                wt.convert_temp(wt.validate_val(src["temp"])),
                windmention,
            ]:
                self.popupgrid.attach(Gtk.Label(item), n1, n2 + 3, 1, 1)
                n2 = n2 + 1
            n1 = n1 + 1

    def update_forecast(self, forec, days):
        # forecast section
        n1 = 1
        for d in days:
            n2 = 20
            src = forec[d]
            # set width
            self.popupgrid.attach(self.h_spacer(120), n1, n2, 1, 1)
            # get day's data, time label optimize?
            self.add_daylabel(d, n1, n2 + 1, 1, 1)
            # set icon
            self.add_icon(src, n1, n2 + 2, 1, 1)
            # prepare wind display
            windmention = self.prepare_windlabel(src)
            # fill in the easy ones
            for item in [
                wt.validate_val(src["sky"]),
                wt.convert_temp(wt.validate_val(src["temp"])),
                windmention,
            ]:
                self.popupgrid.attach(Gtk.Label(item), n1, n2 + 3, 1, 1)
                n2 = n2 + 1
            n1 = n1 + 1

    def set_smallicon(self, image, index):
        image.set_from_pixbuf(small_icons[index])

    def do_get_settings_ui(self):
        """Return the applet settings with given uuid"""
        return BudgieWeatherShowSettings(self.get_applet_settings(self.uuid))

    def do_supports_settings(self):
        """Return True if support setting through Budgie Setting,
        False otherwise.
        """
        return True