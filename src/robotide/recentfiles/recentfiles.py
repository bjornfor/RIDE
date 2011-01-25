#  Copyright 2008-2009 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os.path
import wx

from robotide.publish import RideOpenSuite, RideChangeFormat
from robotide.pluginapi import Plugin, ActionInfo, SeparatorInfo
from robotide.publish.messages import RideNewProject, RideSaved


def normalize_path(path):
    if os.path.basename(path).startswith('__init__.'):
        return os.path.dirname(path)
    return os.path.abspath(path)


class RecentFilesPlugin(Plugin):
    """Add recently opened files to the file menu."""

    def __init__(self, application=None):
        settings = {'recent_files':[], 'max_number_of_files':4}
        Plugin.__init__(self, application, default_settings=settings)

    def enable(self):
        self._save_currently_loaded_suite()
        self._add_recent_files_to_menu()
        self._new_project_path = None
        self.subscribe(self.OnSuiteOpened, RideOpenSuite)
        self.subscribe(self.OnFormatChanged, RideChangeFormat)
        self.subscribe(self.OnNewProjectOpened, RideNewProject)
        self.subscribe(self.OnSaved, RideSaved)
        # TODO: This plugin doesn't currently support resources
        # self._frame.subscribe(self.OnSuiteOpened, ('core', 'open','resource'))

    def disable(self):
        self.unregister_actions()
        self.unsubscribe(self.OnSuiteOpened, RideOpenSuite)
        self.unsubscribe(self.OnNewProjectOpened, RideNewProject)
        self.unsubscribe(self.OnSaved, RideSaved)

    def OnSuiteOpened(self, event):
        # Update menu with CallAfter to ensure ongoing menu selection
        # handling has finished before menu is changed
        wx.CallAfter(self._add_to_recent_files, event.path)
        self._new_project_path = None

    def OnFormatChanged(self, event):
        self._new_project_path = None
        if not event.oldpath:
            return
        oldpath = normalize_path(event.oldpath)
        newpath = normalize_path(event.newpath)
        if oldpath not in self.recent_files:
            return
        index = self.recent_files.index(oldpath)
        self.recent_files[index] = newpath
        self._save_settings_and_update_file_menu()

    def OnNewProjectOpened(self, event):
        self._new_project_path = event.path

    def OnSaved(self, event):
        if self._new_project_path is not None:
            wx.CallAfter(self._add_to_recent_files, self._new_project_path)
            self._new_project_path = None

    def _get_file_menu(self):
        menubar = self.get_menu_bar()
        pos = menubar.FindMenu('File')
        file_menu = menubar.GetMenu(pos)
        return file_menu

    def _save_currently_loaded_suite(self):
        model = self.model
        if model and model.suite:
            self._add_to_recent_files(model.suite.source)

    def _add_to_recent_files(self, file):
        if not file:
            return
        file = normalize_path(file)
        if file in self.recent_files:
            self.recent_files.remove(file)
        self.recent_files.insert(0, file)
        self.recent_files = self.recent_files[0:self.max_number_of_files]
        self._save_settings_and_update_file_menu()

    def _save_settings_and_update_file_menu(self):
        self.save_setting('recent_files', self.recent_files)
        self.unregister_actions()
        self._add_recent_files_to_menu()

    def _add_recent_files_to_menu(self):
        if len(self.recent_files) == 0:
            action = ActionInfo('File', 'No recent files')
            action.set_menu_position(before='Exit')
            self.register_action(action)
        else:
            for n, file in enumerate(self.recent_files):
                self._add_file_to_menu(file, n)
        sep = SeparatorInfo('File')
        sep.set_menu_position(before='Exit')
        self.register_action(sep)

    def _add_file_to_menu(self, file, n):
        entry = RecentFileEntry(n+1, file, self)
        self.register_action(entry.get_action_info())


class RecentFileEntry(object):

    def __init__(self, index, file, plugin):
        self.file = file
        self.index = index
        self.path = normalize_path(self.file)
        self.filename = os.path.basename(file)
        self.plugin = plugin
        self.label = '&%s: %s' % (index, self.filename)
        self.doc = 'Open %s' % self.path

    def OnOpenRecent(self, event):
        self.plugin.open_suite(self.path)

    def get_action_info(self):
        action_info = ActionInfo('File', self.label, self.OnOpenRecent,
                                 doc=self.doc)
        action_info.set_menu_position(before='Exit')
        return action_info
