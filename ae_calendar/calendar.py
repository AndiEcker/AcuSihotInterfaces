# -*- coding: UTF-8 -*-
"""
    calendar screen for kivy apps

    The application need to provide in the kivy.App class:
    * a BooleanProperty landscape that is True if the kivy window/app is horizontal
    * a method date_changed() receiving in the first parameter the selected date value (then *args and **kwargs)
    * a method screen_size_changed()

    version history:
    0.1:  first alpha

    TODO:
    - enhance ae.calendar to be use dependency injection instead of hard-coded call back method names.

"""
import datetime
import calendar
from functools import partial

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

from kivy.app import App
from kivy.properties import ObjectProperty

__version__ = '0.1'


class DateChangeScreen(BoxLayout):
    selected_date = ObjectProperty()  # date value
    built = False

    def build_widgets(self):
        if self.built:  # remove widgets if drawn before
            self.clear_widgets()
        self.built = True

        self.orientation = 'vertical'

        app = App.get_running_app()

        daysGrid = GridLayout(cols=7)
        self.add_widget(daysGrid)

        if app.landscape:
            day_names = calendar.day_name
        else:
            day_names = calendar.day_abbr
        for day_name in day_names:
            daysGrid.add_widget(Label(text=day_name, size_hint=(0.6, 0.24)))

        dayI = datetime.date(self.selected_date.year, self.selected_date.month, 1)
        for _filler in range(dayI.isoweekday() - 1):
            daysGrid.add_widget(Label(text="", size_hint_x=0.6))
        while dayI.month == self.selected_date.month:
            dayLabel = Button(text=str(dayI.day), size_hint_x=0.6, on_press=partial(self.set_day, day=dayI.day))
            if self.selected_date.day == dayI.day:
                dayLabel.background_normal, dayLabel.background_down \
                    = dayLabel.background_down, dayLabel.background_normal
            daysGrid.add_widget(dayLabel)

            dayI += datetime.timedelta(days=1)

        statusGrid = BoxLayout(size_hint_y=0.24 if app.landscape else 0.18,
                               padding=(18 if app.landscape else 9, 9 if app.landscape else 18))
        self.add_widget(statusGrid)

        prevMonth = Button(text="<", on_press=partial(self.set_month, month=self.selected_date.month - 1))
        nextMonth = Button(text=">", on_press=partial(self.set_month, month=self.selected_date.month + 1))
        currDate = Button(text=self.selected_date.strftime('%d / %b / %Y' if app.landscape else '%d/%m/%y'),
                          opacity=0.69,
                          size_hint_x=2.4 if app.landscape else 4.5,
                          size_hint_y=0.9 if app.landscape else 0.81,
                          on_press=partial(app.date_changed, self.selected_date))
        prevYear = Button(text="<<", on_press=partial(self.set_year, year=self.selected_date.year - 1))
        nextYear = Button(text=">>", on_press=partial(self.set_year, year=self.selected_date.year + 1))

        statusGrid.add_widget(prevYear)
        statusGrid.add_widget(prevMonth)
        statusGrid.add_widget(currDate)
        statusGrid.add_widget(nextMonth)
        statusGrid.add_widget(nextYear)

        back = Button(text="Ok", size_hint_y=0.27, on_press=partial(app.date_changed, self.selected_date))
        self.add_widget(back)

    # widget property value change callbacks

    def on_size(self, *_):
        app = App.get_running_app()
        app.screen_size_changed()  # has to be called (only for android device) for to update app.landscape)
        self.build_widgets()

    # UI click callbacks

    def set_day(self, *_, **kwargs):
        self.selected_date = datetime.date(self.selected_date.year, self.selected_date.month, kwargs['day'])
        self.build_widgets()

    def set_month(self, *_, **kwargs):
        year = self.selected_date.year
        month = kwargs['month']
        day = self.selected_date.day
        if month > 12:
            month = 1
            year += 1
        elif month < 1:
            month = 12
            year -= 1
        if day > calendar.monthrange(year, month)[1]:
            day = calendar.monthrange(year, month)[1]
        self.selected_date = datetime.date(year, month, day)
        self.build_widgets()

    def set_year(self, *_, **kwargs):
        self.selected_date = datetime.date(kwargs['year'], self.selected_date.month, self.selected_date.day)
        self.build_widgets()
