import logging
from typing import Tuple

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QMainWindow,
    QShortcut,
    QSizePolicy,
    QStatusBar,
    QWidget,
)

from .adjustments import OpenMediaPlayerAdjustmentsWindowAction
from .base.docking import DockableWidget, ToolBar
from .client.configure import OpenClientSettingsDialogAction
from .client.connect import ConnectStatusLabel, ConnectWideButtonBuilder
from .client.controller import IOController
from .client.socks import AutoReconnectSocket
from .gui.ontop import AlwaysOnTopAction
from .gui.style import initialize_style
from .output.frame import MediaPlayerContentFrame
from .output.fullscreen import FullscreenManager, FullscreenMenu, FullscreenStatusLabel
from .output.orientation import OrientationStatusLabel, ViewpointManager
from .output.playback import (
    FrameResolutionTimeSlider,
    LoopModeManager,
    PlayActions,
    PlaybackModeAction,
)
from .output.size import (
    FrameSizeManager,
    FrameZoomMenu,
    ZoomControlManager,
    ZoomInAction,
    ZoomOutAction,
)
from .output.sound import VolumeManager, VolumePopupButton
from .playlist.files import OpenMediaMenu
from .playlist.player import MediaListPlayer
from .playlist.view import DockablePlaylist, PlaylistWidget
from .preferences import OpenMediaPlayerPreferencesWindowAction

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    initialized = pyqtSignal()
    centralwidgetresized = pyqtSignal()

    def __init__(self, media_player, stylesheet, flags=None):
        QMainWindow.__init__(self, flags)
        self._window_state = None
        self.qapp = QApplication.instance()
        initialize_style(self.qapp, stylesheet)

        self.media_player = media_player

        self.setDockNestingEnabled(True)

        self.create_interface()
        self.create_status_bar()
        self.create_playback_components()
        self.create_other_components()
        self.create_gui_layout()
        self.create_window_shortcuts()

        self.initialized.emit()

    def load_media(self, paths):
        self.playlist_widget.add_media(paths)

    def create_status_bar(self):
        self.status_bar = QStatusBar(parent=self)
        self.connect_status_label = ConnectStatusLabel(
            parent=self.status_bar, socket=self.socket
        )
        self.fullscreen_status_label = FullscreenStatusLabel(
            parent=self.status_bar, fullscreen_mngr=self.fullscreen_mngr
        )
        self.orientation_status_label = OrientationStatusLabel(
            viewpoint_mngr=self.viewpoint_mngr, parent=self.status_bar
        )
        self.status_bar.addPermanentWidget(self.fullscreen_status_label)
        self.status_bar.addPermanentWidget(self.connect_status_label)
        self.status_bar.addPermanentWidget(self.orientation_status_label)
        self.setStatusBar(self.status_bar)

    def create_interface(self):
        self.socket = AutoReconnectSocket()
        self.io_ctrlr = IOController(socket=self.socket)
        self.viewpoint_mngr = ViewpointManager(
            io_ctrlr=self.io_ctrlr, media_player=self.media_player
        )
        self.loop_mode_mngr = LoopModeManager(parent=self)
        self.listplayer = MediaListPlayer(
            viewpoint_mngr=self.viewpoint_mngr,
            loop_mode_mngr=self.loop_mode_mngr,
            media_player=self.media_player,
        )
        self.listplayer.newframe.connect(self.viewpoint_mngr.on_newframe)
        self.frame_size_mngr = FrameSizeManager(
            main_win=self,
            viewpoint_mngr=self.viewpoint_mngr,
            listplayer=self.listplayer,
        )
        self.media_player_content_frame = MediaPlayerContentFrame(
            main_win=self,
            frame_size_mngr=self.frame_size_mngr,
            media_player=self.media_player,
        )
        self.setCentralWidget(self.media_player_content_frame)
        self.zoom_ctrl_mngr = ZoomControlManager(
            main_win=self,
            frame_size_mngr=self.frame_size_mngr,
            media_player=self.media_player,
        )
        self.fullscreen_mngr = FullscreenManager(
            main_win=self,
            main_content_frame=self.media_player_content_frame,
            viewpoint_mngr=self.viewpoint_mngr,
        )

    def create_playback_components(self):
        self.playback_ctrls_slider = FrameResolutionTimeSlider(
            parent=self, listplayer=self.listplayer, media_player=self.media_player
        )
        self.vol_mngr = VolumeManager(
            parent=self, listplayer=self.listplayer, media_player=self.media_player
        )
        self.play_actions = PlayActions(
            parent=self, listplayer=self.listplayer, media_player=self.media_player
        )
        self.playlist_widget = PlaylistWidget(
            listplayer=self.listplayer,
            play_ctrls=self.play_actions,
            parent=self,
        )
        self.dockable_playlist = DockablePlaylist(
            parent=self, playlist_widget=self.playlist_widget
        )
        self.toggle_playlist_act = self.dockable_playlist.toggleViewAction()

        self.playback_mode_act = PlaybackModeAction(
            parent=self, loop_mode_mngr=self.loop_mode_mngr
        )
        self.always_on_top_act = AlwaysOnTopAction(main_win=self)

        self.zoom_in_act = ZoomInAction(parent=self, zoom_ctrl_mngr=self.zoom_ctrl_mngr)
        self.zoom_out_act = ZoomOutAction(
            parent=self, zoom_ctrl_mngr=self.zoom_ctrl_mngr
        )
        self.open_settings_act = OpenClientSettingsDialogAction(main_win=self)
        self.open_adjustments_act = OpenMediaPlayerAdjustmentsWindowAction(
            main_win=self, media_player=self.media_player
        )
        self.open_player_prefs_act = OpenMediaPlayerPreferencesWindowAction(
            main_win=self, media_player=self.media_player
        )

    def create_other_components(self):
        self.open_media_menu = OpenMediaMenu(
            parent=self, playlist_widget=self.playlist_widget
        )
        self.frame_scale_menu = FrameZoomMenu(
            main_win=self,
            zoom_ctrl_mngr=self.zoom_ctrl_mngr,
            listplayer=self.listplayer,
            media_player=self.media_player,
        )
        self.fullscreen_menu = FullscreenMenu(
            main_win=self, fullscreen_mngr=self.fullscreen_mngr
        )
        self.vol_popup_bttn = VolumePopupButton(parent=self, vol_mngr=self.vol_mngr)

        self.connect_wide_button_builder = ConnectWideButtonBuilder(
            parent=self, socket=self.socket
        )

    def create_gui_layout(self):
        # self.setDockOptions(DockOption.AllowNestedDocks | DockOption.AllowTabbedDocks)
        self.setDockNestingEnabled(True)
        # self.setUnifiedTitleAndToolBarOnMac(False)
        # self.setTabbedDock(True)
        self.media_toolbar = ToolBar(
            title="Media",
            objects=[self.open_media_menu, ToolBar.Separator, self.toggle_playlist_act],
            parent=self,
            collapsible=True,
            icon_size=32,
        )
        self.view_toolbar = ToolBar(
            title="View",
            objects=[
                self.frame_scale_menu,
                self.always_on_top_act,
                self.fullscreen_menu,
            ],
            parent=self,
            collapsible=True,
            icon_size=32,
        )
        self.connect_toolbar = ToolBar(
            title="Connect",
            objects=[self.connect_wide_button_builder, self.open_settings_act],
            parent=self,
            collapsible=True,
            icon_size=32,
        )
        self.connect_toolbar.setObjectName("borderedbuttons")

        self.button_bar_widget = QWidget(self)
        self.button_bar_widget.setContentsMargins(0, 0, 0, 0)
        self.button_bar_widget.setLayout(QGridLayout())
        self.button_bar_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.button_bar_widget.layout().addWidget(
            self.view_toolbar, 0, 0, 1, 1, Qt.AlignLeft
        )
        self.button_bar_widget.layout().addWidget(
            self.connect_toolbar, 0, 1, 1, 1, Qt.AlignCenter
        )
        self.button_bar_widget.layout().addWidget(
            self.media_toolbar, 0, 2, 1, 1, Qt.AlignRight
        )
        self.addToolBar(
            Qt.TopToolBarArea,
            ToolBar("Toolbar", parent=self, objects=[self.button_bar_widget]),
        )

        self.playback_slider_widget = QWidget(self)
        self.playback_slider_widget.setContentsMargins(0, 0, 0, 0)
        self.playback_slider_widget.setLayout(QGridLayout())
        self.playback_slider_widget.layout().addWidget(
            self.playback_ctrls_slider, 0, 0, 1, -1, Qt.AlignTop
        )
        self.playback_bttns_left = ToolBar(
            title="Left Control",
            objects=[self.open_player_prefs_act, self.open_adjustments_act],
            collapsible=False,
            parent=self,
            icon_size=32,
        )
        self.playback_bttns_middle = ToolBar(
            title="Playback Controls",
            objects=self.play_actions.actions(),
            parent=self,
            collapsible=False,
            icon_size=60,
        )
        self.playback_bttns_right = ToolBar(
            title="Right Controls",
            objects=[self.playback_mode_act, self.vol_popup_bttn],
            collapsible=False,
            parent=self,
            icon_size=32,
        )
        self.playback_ctrls_widget = QWidget(self)
        self.playback_ctrls_widget.setContentsMargins(0, 0, 0, 0)
        self.playback_ctrls_widget.setLayout(QGridLayout(self.playback_ctrls_widget))
        self.playback_ctrls_widget.layout().addWidget(
            self.playback_slider_widget, 0, 0, 1, -1, Qt.AlignTop
        )
        self.playback_ctrls_widget.layout().addWidget(
            self.playback_bttns_left, 1, 0, 1, 1, Qt.AlignHCenter | Qt.AlignVCenter
        )
        self.playback_ctrls_widget.layout().addWidget(
            self.playback_bttns_middle, 1, 1, 1, 1, Qt.AlignHCenter | Qt.AlignVCenter
        )
        self.playback_ctrls_widget.layout().addWidget(
            self.playback_bttns_right, 1, 2, 1, 1, Qt.AlignJustify | Qt.AlignVCenter
        )
        self.playback_ctrls_dock_widget = DockableWidget(
            title="Playback",
            parent=self,
            widget=self.playback_ctrls_widget,
            w_titlebar=False,
        )

        self.addDockWidget(Qt.RightDockWidgetArea, self.dockable_playlist)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.playback_ctrls_dock_widget)

    def create_window_shortcuts(self):
        # Close window
        self.shortcut_exit = QtWidgets.QShortcut(
            QtGui.QKeySequence.Close, self, self.close
        )

        # Zoom in
        self.shortcut_zoom_in = QShortcut(
            QtGui.QKeySequence.ZoomIn, self, self.zoom_ctrl_mngr.zoom_in
        )

        # Zoom out
        self.shortcut_zoom_out = QShortcut(
            QtGui.QKeySequence.ZoomOut, self, self.zoom_ctrl_mngr.zoom_out
        )

        # Exit fullscreen
        self.ctrl_w = QtWidgets.QShortcut(
            QtGui.QKeySequence.Cancel, self, self.fullscreen_mngr.stop
        )

        # Play media
        self.shortcut_play = QtWidgets.QShortcut(
            QtGui.QKeySequence(Qt.Key_Space), self, self.play_actions.play_pause.trigger
        )

    def _screen_size_threshold_filter(self, target_width, target_height):
        main_win_geo = self.geometry()
        screen = self.qapp.screenAt(main_win_geo.center())
        screen_geo = screen.geometry()
        screen_w = screen_geo.width()
        screen_h = screen_geo.height()
        w = target_width if target_width < screen_w else screen_w
        h = target_height if target_height < screen_h else screen_h
        return w, h

    def _get_win_size(self, media_w, media_h, scale) -> Tuple[int, int]:
        """Calculate total window resize values from current compoment displacement"""
        layout_h = self.layout().totalSizeHint().height()
        return media_w * scale, media_h * scale + layout_h

    def resize_to_media(self, media_w, media_h, scale):
        playlist_is_visible = self.dockable_playlist.isVisible()
        if playlist_is_visible:
            self.dockable_playlist.setVisible(False)

        win_w, win_h = self._get_win_size(media_w, media_h, scale)
        self.resize(win_w, win_h)

        if playlist_is_visible:
            self.dockable_playlist.setVisible(True)

    def showEvent(self, e):
        scale = self.frame_size_mngr.get_media_scale()
        media_w, media_h = self.frame_size_mngr.get_media_size()
        self.resize_to_media(media_w, media_h, scale)
        return super().showEvent(e)

    def sizeHint(self):
        try:
            return self._size_hint
        except AttributeError:
            scale = self.frame_size_mngr.get_media_scale()
            media_w, media_h = self.frame_size_mngr.get_media_size()
            self._size_hint = QSize(*self._get_win_size(media_w, media_h, scale))
        finally:
            return self._size_hint

    def closeEvent(self, e):
        self.fullscreen_mngr.stop()
