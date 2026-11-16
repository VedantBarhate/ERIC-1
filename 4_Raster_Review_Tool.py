import sys
import os
import json
from pathlib import Path

from PIL import Image

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import (
    QImage,
    QPixmap,
    QPainter,
    QPen,
    QColor,
    QFont,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QScrollArea,
    QFrame,
)


# ============================================================
# STATIC PATHS
# ============================================================

# Your RSICD images
IMG_DIR = r"RSICD_optimal-master\RSICD_images"

# Part A directory containing patch_labeling_dataset.json
PART_A_DIR = r"Raster_Labeling_Dataset"

# Module 3 generated JSON files
LABELS_DIR = r"qwen_labels"


# ============================================================
# CLASSES
# ============================================================

CLASSES = [
    "airport",
    "baseballfield",
    "beach",
    "mediumresidential",
    "pond",
    "river",
    "sparseresidential",
    "stadium",
]


# ============================================================
# CONFIG
# ============================================================

GRID = 7
CELL_COUNT = 49

IMAGE_SIZE = 560
RASTER_SIZE = 560


# ============================================================
# COLORS
# ============================================================

BACKGROUND = "#151515"
PANEL = "#202020"
PANEL_2 = "#292929"
TEXT = "#EEEEEE"
MUTED = "#AAAAAA"
ACCENT = "#2E7D32"
SELECTED = "#FFD54F"


# ============================================================
# PIL -> QPIXMAP
# ============================================================

def pil_to_pixmap(image):

    image = image.convert("RGB")

    data = image.tobytes("raw", "RGB")

    qimage = QImage(
        data,
        image.width,
        image.height,
        image.width * 3,
        QImage.Format_RGB888,
    )

    return QPixmap.fromImage(qimage.copy())


# ============================================================
# IMAGE GRID
# ============================================================

class ImageGridWidget(QWidget):

    cell_clicked = Signal(int)

    def __init__(self):

        super().__init__()

        self.pixmap = None
        self.selected_cell = None

        self.setFixedSize(
            IMAGE_SIZE,
            IMAGE_SIZE
        )

    def set_image(self, pixmap):

        self.pixmap = pixmap
        self.update()

    def set_selected_cell(self, cell_id):

        self.selected_cell = cell_id
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.SmoothPixmapTransform
        )

        painter.fillRect(
            self.rect(),
            Qt.black
        )

        if self.pixmap:

            painter.drawPixmap(
                0,
                0,
                IMAGE_SIZE,
                IMAGE_SIZE,
                self.pixmap
            )

        cell_size = IMAGE_SIZE / GRID

        # Grid
        pen = QPen(
            QColor(255, 255, 255)
        )

        pen.setWidth(1)

        painter.setPen(pen)

        for i in range(1, GRID):

            x = int(i * cell_size)
            y = int(i * cell_size)

            painter.drawLine(
                x,
                0,
                x,
                IMAGE_SIZE
            )

            painter.drawLine(
                0,
                y,
                IMAGE_SIZE,
                y
            )

        # Cell numbers
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)

        painter.setFont(font)

        for row in range(GRID):

            for col in range(GRID):

                cid = row * GRID + col

                x = int(col * cell_size)
                y = int(row * cell_size)

                if cid == self.selected_cell:

                    painter.fillRect(
                        QRectF(
                            x,
                            y,
                            cell_size,
                            cell_size
                        ),
                        QColor(
                            255,
                            213,
                            79,
                            70
                        )
                    )

                    selected_pen = QPen(
                        QColor(
                            255,
                            213,
                            79
                        )
                    )

                    selected_pen.setWidth(4)

                    painter.setPen(
                        selected_pen
                    )

                    painter.drawRect(
                        QRectF(
                            x + 2,
                            y + 2,
                            cell_size - 4,
                            cell_size - 4
                        )
                    )

                painter.setPen(
                    QColor(
                        255,
                        255,
                        0
                    )
                )

                painter.drawText(
                    x + 5,
                    y + 16,
                    str(cid)
                )

                painter.setPen(pen)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            cell = self.get_cell(
                event.position().toPoint()
            )

            if cell is not None:

                self.cell_clicked.emit(
                    cell
                )

    def get_cell(self, pos):

        if not (
            0 <= pos.x() < IMAGE_SIZE
            and
            0 <= pos.y() < IMAGE_SIZE
        ):
            return None

        cell_size = IMAGE_SIZE / GRID

        col = int(
            pos.x() / cell_size
        )

        row = int(
            pos.y() / cell_size
        )

        return row * GRID + col


# ============================================================
# RASTER WIDGET
# ============================================================

class RasterWidget(QWidget):

    cell_clicked = Signal(int)

    def __init__(self):

        super().__init__()

        self.labels = {}
        self.selected_cell = None
        self.selected_label = None

        self.painting = False
        self.last_cell = None

        self.setFixedSize(
            RASTER_SIZE,
            RASTER_SIZE
        )

    def set_labels(self, labels):

        self.labels = labels
        self.update()

    def set_selected_cell(self, cell_id):

        self.selected_cell = cell_id
        self.update()

    def set_selected_label(self, label):

        self.selected_label = label
        self.update()

    def color_for_label(self, label):

        palette = [
            "#4E79A7",
            "#F28E2B",
            "#E15759",
            "#76B7B2",
            "#59A14F",
            "#EDC948",
            "#B07AA1",
            "#FF9DA7",
            "#9C755F",
            "#BAB0AC",
            "#6A3D9A",
            "#1B9E77",
            "#D95F02",
            "#7570B3",
            "#E7298A",
            "#66A61E",
            "#E6AB02",
            "#A6761D",
            "#666666",
            "#17BECF",
        ]

        return QColor(
            palette[
                abs(hash(label)) % len(palette)
            ]
        )

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        cell_size = RASTER_SIZE / GRID

        font = QFont()
        font.setPointSize(8)
        font.setBold(True)

        painter.setFont(font)

        for row in range(GRID):

            for col in range(GRID):

                cid = row * GRID + col

                label = self.labels.get(
                    cid,
                    ""
                )

                color = self.color_for_label(
                    label
                )

                # Base cell
                painter.fillRect(
                    QRectF(
                        col * cell_size,
                        row * cell_size,
                        cell_size,
                        cell_size
                    ),
                    color
                )

                # Highlight cells containing
                # currently selected label
                if (
                    self.selected_label
                    and
                    label == self.selected_label
                ):

                    painter.fillRect(
                        QRectF(
                            col * cell_size,
                            row * cell_size,
                            cell_size,
                            cell_size
                        ),
                        QColor(
                            255,
                            255,
                            255,
                            35
                        )
                    )

                # Selected cell
                if cid == self.selected_cell:

                    painter.fillRect(
                        QRectF(
                            col * cell_size,
                            row * cell_size,
                            cell_size,
                            cell_size
                        ),
                        QColor(
                            255,
                            213,
                            79,
                            80
                        )
                    )

                    pen = QPen(
                        QColor(
                            255,
                            213,
                            79
                        )
                    )

                    pen.setWidth(4)

                else:

                    pen = QPen(
                        QColor(
                            255,
                            255,
                            255
                        )
                    )

                    pen.setWidth(1)

                painter.setPen(pen)

                painter.drawRect(
                    QRectF(
                        col * cell_size,
                        row * cell_size,
                        cell_size,
                        cell_size
                    )
                )

                # Label
                text = label

                if len(text) > 12:

                    text = (
                        text[:11]
                        + "…"
                    )

                painter.setPen(
                    Qt.white
                )

                painter.drawText(
                    QRectF(
                        col * cell_size + 3,
                        row * cell_size + 3,
                        cell_size - 6,
                        cell_size - 6
                    ),
                    Qt.AlignCenter
                    | Qt.TextWordWrap,
                    text
                )

        painter.end()

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.painting = True

            cell = self.get_cell(
                event.position().toPoint()
            )

            if cell is not None:

                self.last_cell = cell

                self.cell_clicked.emit(
                    cell
                )

    def mouseMoveEvent(self, event):

        if not self.painting:
            return

        cell = self.get_cell(
            event.position().toPoint()
        )

        if (
            cell is not None
            and
            cell != self.last_cell
        ):

            self.last_cell = cell

            self.cell_clicked.emit(
                cell
            )

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.painting = False
            self.last_cell = None

    def get_cell(self, pos):

        if not (
            0 <= pos.x() < RASTER_SIZE
            and
            0 <= pos.y() < RASTER_SIZE
        ):
            return None

        cell_size = RASTER_SIZE / GRID

        col = int(
            pos.x() / cell_size
        )

        row = int(
            pos.y() / cell_size
        )

        return row * GRID + col


# ============================================================
# CLASS SELECTION SCREEN
# ============================================================

class ClassSelectionWidget(QWidget):

    class_selected = Signal(str)

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            100,
            70,
            100,
            70
        )

        title = QLabel(
            "ERIC — Raster Verification Tool"
        )

        font = QFont()
        font.setPointSize(24)
        font.setBold(True)

        title.setFont(font)

        title.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(title)

        subtitle = QLabel(
            "Select a class to begin verification"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        subtitle.setStyleSheet(
            "color: #AAAAAA; font-size: 14px;"
        )

        layout.addWidget(
            subtitle
        )

        layout.addSpacing(40)

        grid = QGridLayout()

        grid.setSpacing(15)

        for i, class_name in enumerate(
            CLASSES
        ):

            button = QPushButton(
                class_name.upper()
            )

            button.setMinimumSize(
                220,
                80
            )

            button.setFont(
                QFont(
                    "Arial",
                    12,
                    QFont.Bold
                )
            )

            button.clicked.connect(
                lambda checked,
                c=class_name:
                self.class_selected.emit(c)
            )

            row = i // 2
            col = i % 2

            grid.addWidget(
                button,
                row,
                col
            )

        layout.addLayout(grid)

        layout.addStretch()


# ============================================================
# REVIEW SCREEN
# ============================================================

class ReviewWidget(QWidget):

    back_requested = Signal()

    def __init__(
        self,
        scene_name
    ):

        super().__init__()

        self.scene_name = scene_name

        self.label_store = {}

        self.record_by_filename = {}

        self.filenames = []

        self.idx = 0

        self.selected_label = None

        self.selected_cell = None

        self.corrected_file = os.path.join(
            LABELS_DIR,
            f"{scene_name}_verified.json"
        )

        self.build_ui()

        self.load_data()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 15, 20, 10)
        main.setSpacing(8)

        # ========================================================
        # HEADER
        # ========================================================

        header = QHBoxLayout()

        back = QPushButton("← Classes")
        back.setFixedWidth(110)

        back.clicked.connect(
            self.back_requested.emit
        )

        header.addWidget(back)

        title = QLabel(
            f"ERIC — {self.scene_name.upper()}"
        )

        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)

        title.setFont(title_font)

        header.addWidget(title)

        header.addStretch()

        self.progress = QLabel()

        header.addWidget(
            self.progress
        )

        main.addLayout(header)

        # ========================================================
        # IMAGE INFO
        # ========================================================

        self.info = QLabel()

        self.info.setAlignment(
            Qt.AlignCenter
        )

        self.info.setStyleSheet(
            "color: #BBBBBB; font-size: 12px;"
        )

        main.addWidget(
            self.info
        )

        # ========================================================
        # THREE-COLUMN MAIN AREA
        # IMAGE | RASTER | LABELS
        # ========================================================

        content = QHBoxLayout()

        content.setSpacing(12)

        # --------------------------------------------------------
        # COLUMN 1 — IMAGE
        # --------------------------------------------------------

        image_column = QVBoxLayout()

        image_title = QLabel(
            "ORIGINAL IMAGE"
        )

        image_title.setAlignment(
            Qt.AlignCenter
        )

        image_title.setStyleSheet(
            "font-weight: bold; font-size: 13px;"
        )

        image_column.addWidget(
            image_title
        )

        self.image_widget = (
            ImageGridWidget()
        )

        image_column.addWidget(
            self.image_widget,
            alignment=Qt.AlignCenter
        )

        self.image_widget.cell_clicked.connect(
            self.select_image_cell
        )

        content.addLayout(
            image_column,
            1
        )

        # --------------------------------------------------------
        # COLUMN 2 — RASTER
        # --------------------------------------------------------

        raster_column = QVBoxLayout()

        raster_title = QLabel(
            "SEMANTIC RASTER"
        )

        raster_title.setAlignment(
            Qt.AlignCenter
        )

        raster_title.setStyleSheet(
            "font-weight: bold; font-size: 13px;"
        )

        raster_column.addWidget(
            raster_title
        )

        raster_instruction = QLabel(
            "Click / drag to paint"
        )

        raster_instruction.setAlignment(
            Qt.AlignCenter
        )

        raster_instruction.setStyleSheet(
            "color: #888888; font-size: 11px;"
        )

        raster_column.addWidget(
            raster_instruction
        )

        self.raster_widget = (
            RasterWidget()
        )

        raster_column.addWidget(
            self.raster_widget,
            alignment=Qt.AlignCenter
        )

        self.raster_widget.cell_clicked.connect(
            self.paint_cell
        )

        content.addLayout(
            raster_column,
            1
        )

        # --------------------------------------------------------
        # COLUMN 3 — LABELS
        # --------------------------------------------------------

        labels_column = QVBoxLayout()

        labels_title = QLabel(
            "LABELS"
        )

        labels_title.setAlignment(
            Qt.AlignCenter
        )

        labels_title.setStyleSheet(
            "font-weight: bold; font-size: 13px;"
        )

        labels_column.addWidget(
            labels_title
        )

        label_instruction = QLabel(
            "Select a label, then paint the raster"
        )

        label_instruction.setAlignment(
            Qt.AlignCenter
        )

        label_instruction.setWordWrap(
            True
        )

        label_instruction.setStyleSheet(
            "color: #888888; font-size: 11px;"
        )

        labels_column.addWidget(
            label_instruction
        )

        # --------------------------------------------------------
        # Selected label
        # --------------------------------------------------------

        self.selected_info = QLabel(
            "NO LABEL SELECTED"
        )

        self.selected_info.setAlignment(
            Qt.AlignCenter
        )

        self.selected_info.setWordWrap(
            True
        )

        self.selected_info.setMinimumHeight(
            38
        )

        self.selected_info.setStyleSheet(
            """
            QLabel {
                background: #292929;
                border: 1px solid #444444;
                border-radius: 5px;
                padding: 6px;
                color: #FFD54F;
                font-weight: bold;
            }
            """
        )

        labels_column.addWidget(
            self.selected_info
        )

        # --------------------------------------------------------
        # Scrollable label list
        # --------------------------------------------------------

        self.label_scroll = QScrollArea()

        self.label_scroll.setWidgetResizable(
            True
        )

        self.label_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.label_scroll.setFrameShape(
            QFrame.NoFrame
        )

        self.label_container = QWidget()

        self.label_grid = QGridLayout(
            self.label_container
        )

        self.label_grid.setContentsMargins(
            5,
            5,
            5,
            5
        )

        self.label_grid.setSpacing(6)

        self.label_scroll.setWidget(
            self.label_container
        )

        labels_column.addWidget(
            self.label_scroll,
            1
        )

        content.addLayout(
            labels_column,
            1
        )

        main.addLayout(
            content,
            1
        )

        # ========================================================
        # BOTTOM CONTROLS
        # ========================================================

        controls = QHBoxLayout()

        controls.setSpacing(12)

        previous = QPushButton(
            "← Previous"
        )

        previous.setMinimumHeight(
            42
        )

        previous.clicked.connect(
            self.previous_image
        )

        controls.addWidget(
            previous
        )

        controls.addStretch()

        self.flag_button = QPushButton(
            "🚩 Flag"
        )

        self.flag_button.setMinimumHeight(
            42
        )

        self.flag_button.clicked.connect(
            self.toggle_flag
        )

        controls.addWidget(
            self.flag_button
        )

        save = QPushButton(
            "💾 SAVE"
        )

        save.setMinimumHeight(
            42
        )

        save.setMinimumWidth(
            180
        )

        save.setStyleSheet(
            """
            QPushButton {
                background: #2E7D32;
                color: white;
                font-weight: bold;
                padding: 10px 30px;
                border-radius: 5px;
            }

            QPushButton:hover {
                background: #388E3C;
            }
            """
        )

        save.clicked.connect(
            self.save_data
        )

        controls.addWidget(
            save
        )

        controls.addStretch()

        next_button = QPushButton(
            "Next →"
        )

        next_button.setMinimumHeight(
            42
        )

        next_button.clicked.connect(
            self.next_image
        )

        controls.addWidget(
            next_button
        )

        main.addLayout(
            controls
        )

    # --------------------------------------------------------
    # DATA
    # --------------------------------------------------------

    def load_data(self):

        labels_file = os.path.join(
            LABELS_DIR,
            f"{self.scene_name}.json"
        )

        if not os.path.exists(
            labels_file
        ):

            QMessageBox.critical(
                self,
                "Missing Dataset",
                f"Could not find:\n\n"
                f"{labels_file}"
            )

            return

        with open(
            labels_file,
            "r",
            encoding="utf-8"
        ) as f:

            self.label_store = json.load(f)

        # Resume verified dataset
        if os.path.exists(
            self.corrected_file
        ):

            with open(
                self.corrected_file,
                "r",
                encoding="utf-8"
            ) as f:

                self.label_store = json.load(f)

        # Part A
        patch_file = os.path.join(
            PART_A_DIR,
            "patch_labeling_dataset.json"
        )

        if not os.path.exists(
            patch_file
        ):

            QMessageBox.critical(
                self,
                "Missing Part A Dataset",
                f"Could not find:\n\n"
                f"{patch_file}"
            )

            return

        with open(
            patch_file,
            "r",
            encoding="utf-8"
        ) as f:

            records = json.load(f)

        self.record_by_filename = {
            r["filename"]: r
            for r in records
        }

        self.filenames = list(
            self.label_store.keys()
        )

        self.idx = 0

        self.load_current()

    # --------------------------------------------------------
    # CURRENT IMAGE
    # --------------------------------------------------------

    def load_current(self):

        if not self.filenames:
            return

        fname = self.filenames[
            self.idx
        ]

        image_path = os.path.join(
            IMG_DIR,
            fname
        )

        if not os.path.exists(
            image_path
        ):

            QMessageBox.warning(
                self,
                "Missing Image",
                f"Could not find:\n{image_path}"
            )

            return

        image = Image.open(
            image_path
        ).convert("RGB")

        self.image_widget.set_image(
            pil_to_pixmap(image)
        )

        entry = self.label_store[
            fname
        ]

        cells = {
            int(c["cell_id"]): c["label"]
            for c in entry["cells"]
        }

        self.raster_widget.set_labels(
            cells
        )

        record = self.record_by_filename.get(
            fname,
            {}
        )

        terms = record.get(
            "candidate_terms",
            []
        )

        self.build_labels(
            terms
        )

        self.selected_label = None
        self.selected_cell = None

        self.raster_widget.set_selected_label(
            None
        )

        self.raster_widget.set_selected_cell(
            None
        )

        self.image_widget.set_selected_cell(
            None
        )

        flagged = entry.get(
            "needs_review",
            False
        )

        flag_text = (
            " 🚩 FLAGGED"
            if flagged
            else ""
        )

        self.info.setText(
            f"{self.idx + 1} / "
            f"{len(self.filenames)}   "
            f"{fname}"
            f"{flag_text}"
        )

        self.update_progress()

    # --------------------------------------------------------
    # LABEL BUTTONS
    # --------------------------------------------------------

    def build_labels(self, terms):

        # Remove old buttons
        while self.label_grid.count():

            item = self.label_grid.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

        # One label per row
        for row, term in enumerate(terms):

            button = QPushButton(term)

            button.setCheckable(True)

            button.setMinimumHeight(36)

            button.setSizePolicy(
                button.sizePolicy().horizontalPolicy(),
                button.sizePolicy().verticalPolicy()
            )

            button.setStyleSheet(
                """
                QPushButton {
                    text-align: left;
                    padding: 7px 12px;
                    background: #292929;
                    border: 1px solid #444444;
                    border-radius: 4px;
                }

                QPushButton:hover {
                    background: #383838;
                }

                QPushButton:checked {
                    background: #2E7D32;
                    border: 2px solid #81C784;
                    color: white;
                    font-weight: bold;
                }
                """
            )

            button.clicked.connect(
                lambda checked,
                t=term,
                b=button:
                self.select_label(
                    t,
                    b
                )
            )

            self.label_grid.addWidget(
                button,
                row,
                0
            )

        # Make column use available width
        self.label_grid.setColumnStretch(
            0,
            1
        )

    # --------------------------------------------------------
    # SELECT LABEL
    # --------------------------------------------------------

    def select_label(
        self,
        label,
        selected_button
    ):

        self.selected_label = label

        for i in range(
            self.label_grid.count()
        ):

            widget = (
                self.label_grid
                .itemAt(i)
                .widget()
            )

            if widget:
                widget.setChecked(
                    widget is selected_button
                )

        self.selected_info.setText(
            f"SELECTED LABEL: "
            f"{label.upper()}   "
            f"→ Click / drag cells"
        )

        self.raster_widget.set_selected_label(
            label
        )

    # --------------------------------------------------------
    # PAINT
    # --------------------------------------------------------

    def paint_cell(
        self,
        cell_id
    ):

        self.selected_cell = cell_id

        self.image_widget.set_selected_cell(
            cell_id
        )

        self.raster_widget.set_selected_cell(
            cell_id
        )

        if self.selected_label is None:
            return

        fname = self.filenames[
            self.idx
        ]

        entry = self.label_store[
            fname
        ]

        for cell in entry["cells"]:

            if int(
                cell["cell_id"]
            ) == cell_id:

                cell["label"] = (
                    self.selected_label
                )

                break

        cells = {
            int(c["cell_id"]): c["label"]
            for c in entry["cells"]
        }

        self.raster_widget.set_labels(
            cells
        )

    # --------------------------------------------------------
    # IMAGE CELL
    # --------------------------------------------------------

    def select_image_cell(
        self,
        cell_id
    ):

        self.selected_cell = cell_id

        self.image_widget.set_selected_cell(
            cell_id
        )

        self.raster_widget.set_selected_cell(
            cell_id
        )

    # --------------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------------

    def next_image(self):

        if self.idx < len(
            self.filenames
        ) - 1:

            self.idx += 1

            self.load_current()

    def previous_image(self):

        if self.idx > 0:

            self.idx -= 1

            self.load_current()

    # --------------------------------------------------------
    # FLAG
    # --------------------------------------------------------

    def toggle_flag(self):

        fname = self.filenames[
            self.idx
        ]

        entry = self.label_store[
            fname
        ]

        entry["needs_review"] = not entry.get(
            "needs_review",
            False
        )

        self.load_current()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    def save_data(self):

        with open(
            self.corrected_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.label_store,
                f,
                indent=2,
                ensure_ascii=False
            )

        QMessageBox.information(
            self,
            "Saved",
            f"Saved:\n\n"
            f"{self.corrected_file}"
        )

    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    def update_progress(self):

        self.progress.setText(
            f"{self.idx + 1} / "
            f"{len(self.filenames)}"
        )

    # --------------------------------------------------------
    # KEYBOARD
    # --------------------------------------------------------

    def keyPressEvent(self, event):

        if event.key() == Qt.Key_Right:
            self.next_image()

        elif event.key() == Qt.Key_Left:
            self.previous_image()

        elif event.key() == Qt.Key_S:
            self.save_data()

        elif event.key() == Qt.Key_F:
            self.toggle_flag()

        else:
            super().keyPressEvent(event)


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "ERIC — Raster Verification Tool"
        )

        self.resize(
            1450,
            950
        )

        self.setStyleSheet(
            """
            QMainWindow {
                background: #151515;
            }

            QWidget {
                background: #151515;
                color: #EEEEEE;
            }

            QPushButton {
                background: #292929;
                color: #EEEEEE;
                border: 1px solid #444444;
                border-radius: 5px;
                padding: 8px 12px;
            }

            QPushButton:hover {
                background: #383838;
            }

            QPushButton:checked {
                background: #2E7D32;
                color: white;
                border: 2px solid white;
            }
            """
        )

        self.show_class_selection()

    def show_class_selection(self):

        widget = ClassSelectionWidget()

        widget.class_selected.connect(
            self.open_class
        )

        self.setCentralWidget(
            widget
        )

    def open_class(self, scene_name):

        review = ReviewWidget(
            scene_name
        )

        review.back_requested.connect(
            self.show_class_selection
        )

        self.setCentralWidget(
            review
        )


# ============================================================
# MAIN
# ============================================================

def main():

    app = QApplication(
        sys.argv
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()