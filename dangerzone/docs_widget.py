import os
from PyQt5 import QtCore, QtGui, QtWidgets


class DropHereLabel(QtWidgets.QLabel):
    """
    When there are no files in the FileList yet, display the "drop files here" message and graphic
    """

    def __init__(self, global_common, parent, image=False):
        self.parent = parent
        super(DropHereLabel, self).__init__(parent=parent)

        self.global_common = global_common

        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)

        if image:
            self.setPixmap(
                QtGui.QPixmap.fromImage(
                    QtGui.QImage(self.global_common.get_resource_path("icon.png"))
                )
            )
        else:
            self.setText("Drag and drop files to convert to safe PDFs")
            self.setStyleSheet(self.global_common.css["DocsWidget DropHereLabel"])

        self.hide()

    def dragEnterEvent(self, event):
        self.parent.drop_here_image.hide()
        self.parent.drop_here_text.hide()
        event.accept()


class DropCountLabel(QtWidgets.QLabel):
    """
    While dragging files over the FileList, this counter displays the number of files you're dragging
    """

    def __init__(self, global_common, parent):
        self.parent = parent
        super(DropCountLabel, self).__init__(parent=parent)

        self.global_common = global_common

        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setText("Drag and drop files to convert")
        self.setStyleSheet(self.global_common.css["DocsWidget DropCountLabel"])
        self.hide()

    def dragEnterEvent(self, event):
        self.hide()
        event.accept()


class FileList(QtWidgets.QListWidget):
    """
    The list of files
    """

    files_dropped = QtCore.pyqtSignal()
    files_updated = QtCore.pyqtSignal()

    def __init__(self, global_common, parent=None):
        super(FileList, self).__init__(parent)

        self.global_common = global_common

        self.setAcceptDrops(True)
        self.setIconSize(QtCore.QSize(32, 32))
        self.setSortingEnabled(True)
        self.setMinimumHeight(160)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.drop_here_image = DropHereLabel(self.global_common, self, True)
        self.drop_here_text = DropHereLabel(self.global_common, self, False)
        self.drop_count = DropCountLabel(self.global_common, self)
        self.resizeEvent(None)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

    def update(self):
        """
        Update the GUI elements based on the current state
        """
        # File list should have a background image if empty
        if self.count() == 0:
            self.drop_here_image.show()
            self.drop_here_text.show()
        else:
            self.drop_here_image.hide()
            self.drop_here_text.hide()

    def resizeEvent(self, event):
        """
        When the widget is resized, resize the drop files image and text
        """
        offset = 70
        self.drop_here_image.setGeometry(0, 0, self.width(), self.height() - offset)
        self.drop_here_text.setGeometry(0, offset, self.width(), self.height() - offset)

        if self.count() > 0:
            # Add and delete an empty item, to force all items to get redrawn
            item = QtWidgets.QListWidgetItem("fake item")
            self.addItem(item)
            self.takeItem(self.row(item))
            self.update()

            # Extend any filenames that were truncated to fit the window
            # We use 200 as a rough guess at how wide the 'file size + delete button' widget is
            # and extend based on the overall width minus that amount.
            for index in range(self.count()):
                metrics = QtGui.QFontMetrics(self.item(index).font())
                elided = metrics.elidedText(
                    self.item(index).basename, QtCore.Qt.ElideRight, self.width() - 200
                )
                self.item(index).setText(elided)

    def dragEnterEvent(self, event):
        """
        dragEnterEvent for dragging files and directories into the widget
        """
        if event.mimeData().hasUrls:
            self.setStyleSheet(self.global_common.css["DocsWidget FileList DragEnter"])
            count = len(event.mimeData().urls())
            self.drop_count.setText(f"+{count}")

            size_hint = self.drop_count.sizeHint()
            self.drop_count.setGeometry(
                self.width() - size_hint.width() - 10,
                self.height() - size_hint.height() - 10,
                size_hint.width(),
                size_hint.height(),
            )
            self.drop_count.show()
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """
        dragLeaveEvent for dragging files and directories into the widget
        """
        self.setStyleSheet(self.global_common.css["DocsWidget FileList DragLeave"])
        self.drop_count.hide()
        event.accept()
        self.update()

    def dragMoveEvent(self, event):
        """
        dragMoveEvent for dragging files into the widget
        """
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """
        dropEvent for dragging files and directories into the widget
        """
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                filename = str(url.toLocalFile())
                self.add_file(filename)
        else:
            event.ignore()

        self.setStyleSheet(self.global_common.css["DocsWidget FileList DragLeave"])
        self.drop_count.hide()

        self.files_dropped.emit()

    def add_file(self, filename):
        """
        Add a file to this widget
        """
        filenames = []
        for index in range(self.count()):
            filenames.append(self.item(index).filename)

        if filename not in filenames:
            # TODO: Make sure the file is a supported format, and is readable

            # if not os.access(filename, os.R_OK):
            #     Alert(self.common, strings._("not_a_readable_file").format(filename))
            #     return

            fileinfo = QtCore.QFileInfo(filename)
            ip = QtWidgets.QFileIconProvider()
            icon = ip.icon(fileinfo)

            if os.path.isfile(filename):
                size_bytes = fileinfo.size()
                size_readable = self.global_common.human_readable_filesize(size_bytes)
            else:
                size_bytes = self.global_common.dir_size(filename)
                size_readable = self.global_common.human_readable_filesize(size_bytes)

            # Create a new item
            item = QtWidgets.QListWidgetItem()
            item.setIcon(icon)
            item.size_bytes = size_bytes

            # Item's filename attribute and size labels
            item.filename = filename
            item_size = QtWidgets.QLabel(size_readable)
            item_size.setStyleSheet(
                self.global_common.css["DocsWidget FileList FileSize"]
            )

            item.basename = os.path.basename(filename.rstrip("/"))
            # Use the basename as the method with which to sort the list
            metrics = QtGui.QFontMetrics(item.font())
            elided = metrics.elidedText(
                item.basename, QtCore.Qt.ElideRight, self.sizeHint().width()
            )
            item.setData(QtCore.Qt.DisplayRole, elided)

            # Item's delete button
            def delete_item():
                itemrow = self.row(item)
                self.takeItem(itemrow)
                self.files_updated.emit()

            item.item_button = QtWidgets.QPushButton()
            item.item_button.setDefault(False)
            item.item_button.setFlat(True)
            item.item_button.setIcon(
                QtGui.QIcon(self.global_common.get_resource_path("delete_file.png"))
            )
            item.item_button.clicked.connect(delete_item)
            item.item_button.setSizePolicy(
                QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
            )

            # Item info widget, with a white background
            item_info_layout = QtWidgets.QHBoxLayout()
            item_info_layout.setContentsMargins(0, 0, 0, 0)
            item_info_layout.addWidget(item_size)
            item_info_layout.addWidget(item.item_button)
            item_info = QtWidgets.QWidget()
            item_info.setObjectName("item-info")
            item_info.setLayout(item_info_layout)

            # Create the item's widget and layouts
            item_hlayout = QtWidgets.QHBoxLayout()
            item_hlayout.addStretch()
            item_hlayout.addWidget(item_info)
            widget = QtWidgets.QWidget()
            widget.setLayout(item_hlayout)

            item.setSizeHint(widget.sizeHint())

            self.addItem(item)
            self.setItemWidget(item, widget)

            self.files_updated.emit()


class DocsWidget(QtWidgets.QWidget):
    """
    The list of files, their status, and buttons to add and delete them
    """

    document_selected = QtCore.pyqtSignal()

    def __init__(self, global_common, common):
        super(DocsWidget, self).__init__()
        self.global_common = global_common
        self.common = common

        # File list
        self.file_list = FileList(self.global_common)
        self.file_list.itemSelectionChanged.connect(self.update)
        self.file_list.files_dropped.connect(self.update)
        self.file_list.files_updated.connect(self.update)

        # Buttons
        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.clicked.connect(self.add)
        self.delete_button = QtWidgets.QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.file_list)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.update()

    def update(self):
        """
        Update the GUI elements based on the current state
        """
        # TODO: If conversion is in process, hide the buttons, the individual delete buttons for
        # each file, and show the "pending", "current", "success", "fail" statuses of each file

        # Update the file list
        self.file_list.update()

    def add(self):
        """
        Add button clicked
        """
        files = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select documents to convert",
            filter="Documents (*.pdf *.docx *.doc *.docm *.xlsx *.xls *.pptx *.ppt *.odt *.odg *.odp *.ods *.jpg *.jpeg *.gif *.png *.tif *.tiff)",
        )
        filenames = files[0]
        for filename in filenames:
            self.file_list.add_file(filename)
            # TODO: fix this
            self.common.document_filename = filename
            self.document_selected.emit()

        self.file_list.setCurrentItem(None)
        self.update()

    def delete(self):
        """
        Delete button clicked
        """
        selected = self.file_list.selectedItems()
        for item in selected:
            itemrow = self.file_list.row(item)
            self.file_list.takeItem(itemrow)
        self.file_list.files_updated.emit()

        self.file_list.setCurrentItem(None)
        self.update()

    def get_filenames(self):
        """
        Return the list of file and folder names
        """
        filenames = []
        for index in range(self.file_list.count()):
            filenames.append(self.file_list.item(index).filename)
        return filenames
