import logging
import os
from base.docking import DockableWidget
from base.popup import PopupWindowAction, PopupWindowWidget
from gui import icons
from playlist import files
from playlist.model import MediaItem, PlaylistModel
from PyQt5 import QtGui
from PyQt5.QtCore import QModelIndex, QPoint, Qt, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QHeaderView,
    QMainWindow,
    QMenu,
    QShortcut,
    QStatusBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)


class PlaylistViewHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.sectionCountChanged.connect(self.on_sectionCountChanged)

    def on_sectionCountChanged(self, oldCount, newCount):
        if oldCount == newCount:
            return None

        self.actions = []
        for index in range(newCount):
            name = self.model().headerData(index, Qt.Horizontal, Qt.DisplayRole)
            action = QAction(str(name), self)
            # Store section_index for retreival on trigger
            action.setData(index)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(self.toggle_section)
            self.actions.append(action)

        log.info(f"sectionCountChanged oldCount={oldCount}, newCount={newCount}")

    @pyqtSlot(bool)
    def toggle_section(self, hide: bool):
        action: QAction = self.sender()
        logical_index: int = action.data()
        self.setSectionHidden(logical_index, not hide)

    def show_context_menu(self, point):
        menu = QMenu(self)
        self.currentSection = self.logicalIndexAt(point)
        for action in self.actions:
            menu.addAction(action)
        menu.exec_(self.mapToGlobal(point))


class PlaylistView(QTableView):
    def __init__(self, listplayer, status_bar: QStatusBar, play_ctrls, parent=None):
        super().__init__(parent=parent)
        self.player = listplayer
        self.status_bar = status_bar
        self.play_ctrls = play_ctrls

        self.setSelectionBehavior(self.SelectRows)
        self.setDragDropMode(self.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setEditTriggers(QTableView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setDropIndicatorShown(True)
        self.setHorizontalHeader(PlaylistViewHeader(parent=self))
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # Create shortcuts
        self.rem_selected_items_shortcut = QShortcut(self)
        self.rem_selected_items_shortcut.setKey(QKeySequence.Delete)
        self.rem_selected_items_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.rem_selected_items_shortcut.activated.connect(self.remove_selected_items)

        self.play_selected_item_shortcut = QShortcut(self)
        self.play_selected_item_shortcut.setKey(Qt.Key_Return)
        self.play_selected_item_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.play_selected_item_shortcut.activated.connect(self.play_selected_item)

        self.setModel(PlaylistModel())

        # Setup signals
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.doubleClicked.connect(self.on_doubleClicked)
        self.selectionModel().selectionChanged.connect(self.on_selectionChanged)

    def showEvent(self, e):
        if self.model().rowCount():
            if not self.selectionModel().hasSelection():
                self.setCurrentIndex(self.model().item(0).index())
        self.setFocus()

    @pyqtSlot()
    def play_selected_item(self):
        self.player.load_media(index=self.currentIndex())
        self.player.mp.play()

    def mousePressEvent(self, e):
        """Clear both row and current index selections when clicking away from items."""
        clicked_index = self.indexAt(e.pos())
        if clicked_index.isValid():
            item = self.model().item(clicked_index.row())
            status_tip = item.data(role=Qt.DisplayRole)
            self.status_bar.showMessage(status_tip)
        else:
            self.selectionModel().clear()
        return super().mousePressEvent(e)

    def on_selectionChanged(self, selected, deselected):
        if not selected:
            self.selectionModel().clear()

    @pyqtSlot(QModelIndex)
    def on_doubleClicked(self, index):
        self.player.load_media(index=index)
        self.player.mp.play()

    def dropEvent(self, e):
        dragged_index = self.currentIndex()
        dropped_index = self.indexAt(e.pos())

        log.debug(
            f"dragged_index={dragged_index.row(), dragged_index.column()} dropped_index={dropped_index.row(), dropped_index.column()} action={e.dropAction()} source={e.source()}"
        )

        if dropped_index.row() == -1:
            return None

        model = self.model()
        item = model.takeRow(dragged_index.row())
        model.insertRow(dropped_index.row(), item)
        self.setCurrentIndex(dropped_index)
        e.ignore()

    @pyqtSlot(int)
    def on_model_rowCountChanged(self, count):
        """Enable/disable GUI elements when media is added or removed"""
        if count:
            self.play_ctrls.setEnabled(True)
        else:
            self.play_ctrls.setEnabled(False)

    def setModel(self, model):
        # Disconnect previous model
        if self.model():
            self.model().rowCountChanged.disconnect()
        # Connect this model
        model.rowCountChanged.connect(self.on_model_rowCountChanged)
        model.rowCountChanged.connect(self.player.on_playlist_rowCountChanged)
        super().setModel(model)

    def selected_items(self):
        items = []
        for i in self.selectionModel().selectedRows():
            items.append(self.model().itemFromIndex(i))
        return items

    def show_context_menu(self, pos: QPoint):
        selected_items = self.selected_items()
        if len(selected_items) <= 1:
            rem_selected_text = f"Remove '{selected_items[0].data(Qt.DisplayRole)}'"
        else:
            rem_selected_text = f"Remove {len(selected_items)} items"
        menu = QMenu(self)
        menu.addAction(
            icons.get("file_remove"),
            rem_selected_text,
            self.remove_selected_items,
            self.rem_selected_items_shortcut.key(),
        )
        menu.exec_(self.mapToGlobal(pos))

    @pyqtSlot()
    def remove_selected_items(self):
        indexes = self.selectionModel().selectedRows()
        items = [self.model().itemFromIndex(i) for i in indexes]
        self.remove_items(items)

    def remove_items(self, items):
        # Create a status message
        if len(items) == 1:
            status_msg = f"Removed '{items[0].data(Qt.DisplayRole)}'"
        else:
            status_msg = f"Removed {len(items)} items"

        # Unload from player
        self.player.unload_media(items=items)

        # Remove from model
        start_row = self.model().indexFromItem(items[0]).row()
        num_rows = len(items)
        self.model().removeRows(start_row, num_rows)

        # Push status message
        self.status_bar.showMessage(status_msg)


class PlaylistWidget(QWidget):
    def __init__(self, listplayer, play_ctrls, ffprobe_cmd: str, parent: QMainWindow):
        super().__init__(parent=parent)
        self.player = listplayer
        self.play_ctrls = play_ctrls
        self.ffprobe_cmd = ffprobe_cmd
        self.view = PlaylistView(
            listplayer=self.player,
            play_ctrls=self.play_ctrls,
            status_bar=self.parent().statusBar(),
        )

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.view)

    def add_media(self, paths=[]):
        # print(f"{paths=}")
        media_paths=paths
        # [print(os.path.isfile(p)) for p in media_paths]
        # media_paths = files.get_media_paths(paths)
        if not media_paths:
            log.error(f"No media paths found in {media_paths}")
            return

        model = self.view.model()
        for media_path in media_paths:
            item = MediaItem(media_path, ffprobe_cmd=self.ffprobe_cmd)
            print(item)
            model.appendRow(item)

        first_item = self.view.model().item(0)
        if first_item:
            self.player.load_media(index=first_item.index())


class DockablePlaylist(DockableWidget):
    def __init__(self, parent, playlist_widget):
        super().__init__(title="Playlist", parent=parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setWidget(playlist_widget)
        self.setVisible(False)
        self.toggleViewAction().setIcon(icons.get("open_playlist"))
        self.toggleViewAction().setEnabled(True)
        self.toggleViewAction().setShortcut(QtGui.QKeySequence("Ctrl+M"))
        self.toggleViewAction().setText(
            f"Open Playlist {self.toggleViewAction().shortcut().toString()}"
        )


class PlaylistPopupWindow(PopupWindowWidget):
    def __init__(self, playlist_widget, main_win):
        super().__init__(parent=None)
        self.playlist_widget = playlist_widget
        self.main_win = main_win

        self.setWindowTitle("Playlist")
        self.setLayout(QVBoxLayout(self))

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.playlist_widget)

    def showEvent(self, e):
        width = self.sizeHint().width()
        pos = self.main_win.pos()
        pos.setX(pos.x() - width)
        self.move(pos)
        super().showEvent(e)


class OpenPlaylistPopupWindowAction(PopupWindowAction):
    def __init__(self, playlist_widget, main_win):
        self.playlist_win = PlaylistPopupWindow(
            playlist_widget=playlist_widget, main_win=main_win
        )
        super().__init__(
            icon=icons.get("open_playlist"),
            text="Open Playlist",
            widget=self.playlist_win,
            main_win=main_win,
        )
