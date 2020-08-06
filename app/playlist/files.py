import logging
import os
from typing import Union

import vlcqt
from gui import icons
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QFileDialog, QMenu

log = logging.getLogger(__name__)


def get_file_paths(paths: list):
    file_paths = []
    for path in paths:
        if os.path.isfile(path):
            file_paths.append(path)
        elif os.path.isdir(path):
            for i in os.scandir(path):
                if i.is_file():
                    file_paths.append(i.path)
        else:
            log.warning(f"Path does not exist: {path}")
    return file_paths


def get_media_object(path: str):
    media = vlcqt.Media(path)
    media.parse()
    iter_tracks = media.tracks_get()
    if not iter_tracks:
        return None
    else:
        return media


def get_media_objects(paths: Union[list, str]):
    if isinstance(paths, str):
        paths = [paths]

    media_objects = []
    for p in get_file_paths(paths):
        obj = get_media_object(p)
        if obj:
            media_objects.append(obj)

    return media_objects


def get_media_paths(paths):
    if isinstance(paths, str):
        paths = [paths]

    file_paths = []
    for path in [string for string in paths if string]:
        if not os.path.exists(path):
            log.error(f"PATH NOT FOUND path={path}")
        elif os.path.isfile(path):
            file_paths.append(path)
        elif os.path.isdir(path):
            for i in os.scandir(path):
                if i.is_file():
                    file_paths.append(i.path)
    print(f"{file_paths}")
    media_paths = []
    for path in file_paths:
        print(path)
        _media = vlcqt.Media(path)
        print(_media)
        _media.parse()
        iter_tracks = _media.tracks_get()
        print(iter_tracks)
        if not iter_tracks:
            continue
        media_paths.append(os.path.abspath(path))
        del _media

    return media_paths


class OpenFileAction(QAction):
    def __init__(self, parent, playlist_widget):
        super().__init__(parent=parent)
        self.parent = parent
        self.playlist_widget = playlist_widget
        self.setIcon(icons.get("open_file"))
        self.setText("Open file")
        self.setShortcut("Ctrl+O")
        self.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        # self.setShortcutVisibleInContextMenu(True)

        self.triggered.connect(self.on_triggered)

    def on_triggered(self):
        file_path, filter_desc = QFileDialog.getOpenFileName(
            self.parent, self.text(), directory="media"
        )
        if file_path:
            self.playlist_widget.add_media([file_path])


class OpenMultipleAction(QAction):
    def __init__(self, parent, playlist_widget):
        super().__init__(parent=parent)
        self.parent = parent
        self.playlist_widget = playlist_widget
        self.setIcon(icons.get("open_multiple"))
        self.setText("Open Multiple Files")
        self.setShortcut("Ctrl+M")
        self.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        # self.setShortcutVisibleInContextMenu(True)

        self.triggered.connect(self.on_triggered)

    def on_triggered(self):
        file_paths, filter_desc = QFileDialog.getOpenFileNames(
            self.parent, self.text(), directory="media"
        )
        if file_paths:
            self.playlist_widget.add_media(file_paths)


class OpenMediaMenu(QMenu):
    def __init__(self, parent, playlist_widget):
        super().__init__(parent=parent)
        self.parent = parent
        self.playlist_widget = playlist_widget
        self.setIcon(icons.get("open_file_menu"))
        self.setTitle("Open Media")
        self.addAction(OpenMultipleAction(parent=self, playlist_widget=playlist_widget))
        self.addAction(OpenFileAction(parent=self, playlist_widget=playlist_widget))
