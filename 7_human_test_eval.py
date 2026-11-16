import csv
import json
import random
import sys
import html
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from PyQt6.QtCore import Qt, QSize, QEvent
from PyQt6.QtGui import QPixmap, QImage, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QScrollArea,
    QMessageBox, QFileDialog, QProgressBar, QSplitter, QFrame
)

# ---------------------------------------------------------------------------
# CONFIGURATION: update these paths for your desktop
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

PREDICTION_PATHS = {
    "6a": BASE_DIR / "6a_ImgTransformerCaptioner/test_predictions.json",
    "6b": BASE_DIR / "6b_RasterTransformerCaptioner/test_evaluation/test_prediction.json",
    "6e": BASE_DIR / "6e_ImagePlusRasterTransformerCaptioner/evaluation/test_prediction.json",
}

IMAGE_DIR = BASE_DIR / "RSICD_optimal-master/RSICD_images"
OUTPUT_DIR = BASE_DIR / "Human_Evaluation_Output"

# Stable seed means the blinded candidate order stays the same when resuming.
RANDOM_SEED = 20261024

# ---------------------------------------------------------------------------
# DISPLAY SETTINGS
# ---------------------------------------------------------------------------
IMAGE_SCALE = 2.5      # RSICD images are 224x224 -> shown at 560x560
FONT_POINT_SIZE = 14   # roughly 1.5x the default (~9pt)

# Zoom limits / steps (Ctrl + mouse wheel, Ctrl + '+' / '-', Ctrl + 0 to reset)
FONT_MIN, FONT_MAX, FONT_STEP = 8, 40, 1
IMAGE_SCALE_MIN, IMAGE_SCALE_MAX, IMAGE_SCALE_STEP = 1.0, 5.0, 0.25
BASE_FONT_FOR_LAYOUT = 14  # layout sizes below are tuned for this font size

# Dark-mode palette: neutral slate surfaces with a single restrained accent
COL_BG = "#121417"
COL_PANEL = "#1a1d22"
COL_PANEL_ALT = "#22262d"
COL_BORDER = "#2c313a"
COL_TEXT = "#e4e7ec"
COL_MUTED = "#8b93a1"
COL_ACCENT = "#5b8def"
COL_ACCENT_HOVER = "#7aa3f5"
COL_ACCENT_PRESSED = "#4a78d4"

CRITERIA = [
    ("factual_correctness", "Factual correctness", 0.35,
     "Are the objects and details stated in the caption visibly true? Penalize hallucinations."),
    ("scene_coverage", "Object and scene coverage", 0.25,
     "Does it capture the important objects and scene characteristics?"),
    ("spatial_quality", "Spatial and relational quality", 0.25,
     "Are object positions and relationships described correctly? Do not reward unsupported claims."),
    ("language_quality", "Language quality", 0.15,
     "Is the caption clear, grammatical, and concise?"),
]


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {COL_BG};
        color: {COL_TEXT};
    }}
    QLabel {{
        background: transparent;
    }}
    QToolTip {{
        background-color: {COL_PANEL_ALT};
        color: {COL_TEXT};
        border: 1px solid {COL_BORDER};
        padding: 6px;
    }}
    QGroupBox {{
        background-color: {COL_PANEL};
        border: 1px solid {COL_BORDER};
        border-radius: 8px;
        margin-top: 22px;
        padding: 14px 10px 10px 10px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 14px;
        padding: 0 8px;
        background-color: {COL_BG};
        color: {COL_MUTED};
    }}
    QGroupBox QLabel {{
        font-weight: normal;
    }}
    QLabel#caption {{
        background-color: {COL_PANEL_ALT};
        border-left: 3px solid {COL_ACCENT};
        border-radius: 4px;
        padding: 10px 12px;
        color: {COL_TEXT};
    }}
    QLabel#imageLabel {{
        background-color: #0c0e10;
        border: 1px solid {COL_BORDER};
        border-radius: 8px;
        color: {COL_MUTED};
    }}
    QLabel#progressLabel {{
        color: {COL_TEXT};
        font-weight: 600;
    }}
    QLabel#note {{
        color: {COL_MUTED};
    }}
    QProgressBar {{
        background-color: {COL_PANEL};
        border: 1px solid {COL_BORDER};
        border-radius: 6px;
        text-align: center;
        color: {COL_TEXT};
    }}
    QProgressBar::chunk {{
        border-radius: 5px;
        background-color: {COL_ACCENT};
    }}
    QComboBox {{
        background-color: {COL_PANEL_ALT};
        border: 1px solid {COL_BORDER};
        border-radius: 6px;
        padding: 4px 10px;
        color: {COL_TEXT};
    }}
    QComboBox:hover {{
        border-color: {COL_ACCENT};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COL_PANEL_ALT};
        color: {COL_TEXT};
        border: 1px solid {COL_BORDER};
        selection-background-color: {COL_ACCENT};
        selection-color: #ffffff;
        outline: none;
    }}
    QPushButton {{
        background-color: {COL_PANEL_ALT};
        color: {COL_TEXT};
        border: 1px solid {COL_BORDER};
        border-radius: 6px;
        padding: 9px 20px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: #2b3038;
        border-color: #3a404b;
    }}
    QPushButton:pressed {{
        background-color: {COL_BG};
    }}
    QPushButton:disabled {{
        color: #5a616d;
        background-color: {COL_PANEL};
        border-color: {COL_PANEL_ALT};
    }}
    QPushButton#nextBtn {{
        background-color: {COL_ACCENT};
        border-color: {COL_ACCENT};
        color: #ffffff;
        font-weight: 600;
    }}
    QPushButton#nextBtn:hover {{
        background-color: {COL_ACCENT_HOVER};
        border-color: {COL_ACCENT_HOVER};
    }}
    QPushButton#nextBtn:pressed {{
        background-color: {COL_ACCENT_PRESSED};
    }}
    QPushButton#nextBtn:disabled {{
        background-color: {COL_PANEL};
        border-color: {COL_PANEL_ALT};
        color: #5a616d;
    }}
    QPushButton#finishBtn {{
        border-color: {COL_ACCENT};
        color: {COL_ACCENT_HOVER};
    }}
    QPushButton#finishBtn:hover {{
        background-color: {COL_PANEL_ALT};
        border-color: {COL_ACCENT_HOVER};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: {COL_BG};
        width: 12px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {COL_BORDER};
        border-radius: 5px;
        min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #454c59;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QSplitter::handle {{
        background-color: {COL_BORDER};
        width: 1px;
    }}
    QMessageBox {{
        background-color: {COL_PANEL};
    }}
    """


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_records(path: Path, model_name: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Prediction file for Module {model_name} was not found:\n{path}\n\n"
            "Update PREDICTION_PATHS near the top of human_evaluator.py."
        )

    data = read_json(path)
    # Support either a list of records or a dict containing a list.
    if isinstance(data, dict):
        for key in ("predictions", "records", "data", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    if not isinstance(data, list):
        raise ValueError(f"{path.name}: expected a JSON list of prediction records.")

    result: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"{path.name}: record {i} is not a JSON object.")
        filename = row.get("filename") or row.get("image") or row.get("image_filename")
        prediction = row.get("prediction") or row.get("generated_caption") or row.get("caption")
        references = row.get("references") or row.get("reference_captions") or row.get("captions")

        if not filename:
            raise ValueError(f"{path.name}: record {i} is missing filename.")
        if prediction is None:
            raise ValueError(f"{path.name}: record for {filename!r} is missing prediction.")
        if isinstance(references, str):
            references = [references]
        if not isinstance(references, list):
            raise ValueError(f"{path.name}: record for {filename!r} has no references list.")

        filename = Path(str(filename)).name
        if filename in result:
            raise ValueError(f"{path.name}: duplicate filename {filename!r}.")
        result[filename] = {
            "filename": filename,
            "scene": row.get("scene", ""),
            "prediction": str(prediction).strip(),
            "references": [str(x).strip() for x in references if str(x).strip()],
        }
    return result


class CandidatePanel(QGroupBox):
    def __init__(self, label: str, parent=None):
        super().__init__(f"Candidate {label}", parent)
        self.setObjectName(f"cand{label}")
        self.candidate_label = label
        self.caption_label = QLabel()
        self.caption_label.setObjectName("caption")
        self.caption_label.setWordWrap(True)
        self.caption_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.score_boxes: dict[str, QComboBox] = {}
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(self.caption_label)

        for key, title, weight, description in CRITERIA:
            row = QHBoxLayout()
            label_widget = QLabel(f"{title} ({int(weight * 100)}%)")
            label_widget.setToolTip(description)
            label_widget.setWordWrap(True)
            combo = QComboBox()
            combo.addItem("Not rated", None)
            for score in range(1, 6):
                combo.addItem(f"{score} — {['Very poor', 'Poor', 'Acceptable', 'Good', 'Excellent'][score-1]}", score)
            self.score_boxes[key] = combo
            row.addWidget(label_widget, 1)
            row.addWidget(combo)
            layout.addLayout(row)

    def apply_scale(self, f: float):
        self.caption_label.setMinimumHeight(int(90 * f))
        for combo in self.score_boxes.values():
            combo.setMinimumWidth(int(260 * f))
            combo.setMinimumHeight(int(36 * f))

    def set_caption(self, text: str):
        self.caption_label.setText(text or "(Empty caption)")

    def get_scores(self) -> dict[str, int | None]:
        return {key: box.currentData() for key, box in self.score_boxes.items()}

    def set_scores(self, scores: dict[str, Any] | None):
        scores = scores or {}
        for key, box in self.score_boxes.items():
            value = scores.get(key)
            idx = box.findData(value)
            box.setCurrentIndex(idx if idx >= 0 else 0)


class HumanEvaluator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ERIC — Blinded Human Caption Evaluator")
        self.resize(2300, 1400)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.ratings_path = OUTPUT_DIR / "ratings.json"
        self.blind_key_path = OUTPUT_DIR / "blind_key.json"

        self.records_by_model = {
            model: normalize_records(path, model)
            for model, path in PREDICTION_PATHS.items()
        }

        common = set.intersection(*(set(v.keys()) for v in self.records_by_model.values()))
        union = set.union(*(set(v.keys()) for v in self.records_by_model.values()))
        if not common:
            raise ValueError("The three prediction files have no common filenames.")
        missing = {m: sorted(union - set(records)) for m, records in self.records_by_model.items()}
        if any(missing.values()):
            details = "\n".join(
                f"Module {m}: missing {len(names)} common test image(s)"
                for m, names in missing.items() if names
            )
            QMessageBox.warning(
                self, "Prediction set mismatch",
                "Only images present in all three files will be evaluated.\n\n" + details
            )

        self.filenames = sorted(common)
        self.ratings = self._load_ratings()
        self.blind_key = self._load_or_create_blind_key()

        self.index = self._first_unrated_index()
        self.candidate_panels: dict[str, CandidatePanel] = {}
        self.font_pt = FONT_POINT_SIZE
        self.image_scale = IMAGE_SCALE
        self.current_image_path: Path | None = None
        self._build_ui()
        self._setup_zoom()
        self.show_record()
        self._apply_font()

    def _load_ratings(self) -> dict[str, Any]:
        if self.ratings_path.exists():
            try:
                data = read_json(self.ratings_path)
                return data if isinstance(data, dict) else {}
            except Exception:
                QMessageBox.warning(self, "Ratings file", "Could not read existing ratings.json. Starting with an empty rating set.")
        return {}

    def _load_or_create_blind_key(self) -> dict[str, dict[str, str]]:
        if self.blind_key_path.exists():
            try:
                data = read_json(self.blind_key_path)
                if all(fn in data for fn in self.filenames):
                    return data
            except Exception:
                pass

        rng = random.Random(RANDOM_SEED)
        key: dict[str, dict[str, str]] = {}
        for filename in self.filenames:
            models = ["6a", "6b", "6e"]
            rng.shuffle(models)
            key[filename] = dict(zip(["A", "B", "C"], models))
        self._write_json(self.blind_key_path, key)
        return key

    def _first_unrated_index(self) -> int:
        for i, filename in enumerate(self.filenames):
            saved = self.ratings.get(filename, {})
            if not all(
                all(saved.get(label, {}).get(k) in (1, 2, 3, 4, 5) for k, *_ in CRITERIA)
                for label in ("A", "B", "C")
            ):
                return i
        return 0

    def _write_json(self, path: Path, data: Any):
        temp = path.with_suffix(path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp.replace(path)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_label.setObjectName("progressLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        header.addWidget(self.progress_label, 1)
        header.addWidget(self.progress_bar)
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # Left side: image and references.
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        self.image_label = QLabel("Image will appear here")
        self.image_label.setObjectName("imageLabel")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        left_layout.addWidget(self.image_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.scene_label = QLabel()
        self.scene_label.setWordWrap(True)
        left_layout.addWidget(self.scene_label)

        refs_group = QGroupBox("Five reference captions")
        refs_layout = QVBoxLayout(refs_group)
        self.references_label = QLabel()
        self.references_label.setWordWrap(True)
        self.references_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.references_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        refs_scroll = QScrollArea()
        refs_scroll.setWidgetResizable(True)
        refs_scroll.setWidget(self.references_label)
        refs_layout.addWidget(refs_scroll)
        left_layout.addWidget(refs_group, 1)
        splitter.addWidget(left_widget)

        # Right side: blinded candidates and ratings.
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        note = QLabel(
            "Score each caption independently. Judge only what the image supports; "
            "do not infer model identity. Hover over criterion names for guidance.  "
            "Zoom text: Ctrl + mouse wheel or Ctrl + / Ctrl -.  "
            "Zoom image: Ctrl + Shift + wheel or Ctrl + Shift + / -.  Ctrl + 0 resets."
        )
        note.setObjectName("note")
        note.setWordWrap(True)
        right_layout.addWidget(note)

        candidates_scroll = QScrollArea()
        candidates_scroll.setWidgetResizable(True)
        candidates_container = QWidget()
        candidates_container.setStyleSheet("background: transparent;")
        candidates_layout = QVBoxLayout(candidates_container)
        for label in ("A", "B", "C"):
            panel = CandidatePanel(label)
            self.candidate_panels[label] = panel
            candidates_layout.addWidget(panel)
        candidates_layout.addStretch(1)
        candidates_scroll.setWidget(candidates_container)
        right_layout.addWidget(candidates_scroll, 1)
        splitter.addWidget(right_widget)
        splitter.setSizes([780, 1500])

        # Navigation controls.
        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.previous_button = QPushButton("← Previous")
        self.save_button = QPushButton("Save ratings")
        self.next_button = QPushButton("Save & Next →")
        self.skip_button = QPushButton("Next without saving")
        self.export_button = QPushButton("Export current results")
        self.finish_button = QPushButton("Finish & reveal model mapping")
        self.previous_button.setObjectName("prevBtn")
        self.save_button.setObjectName("saveBtn")
        self.next_button.setObjectName("nextBtn")
        self.skip_button.setObjectName("skipBtn")
        self.export_button.setObjectName("exportBtn")
        self.finish_button.setObjectName("finishBtn")
        controls.addWidget(self.previous_button)
        controls.addWidget(self.save_button)
        controls.addWidget(self.next_button)
        controls.addWidget(self.skip_button)
        controls.addStretch(1)
        controls.addWidget(self.export_button)
        controls.addWidget(self.finish_button)
        root.addLayout(controls)

        self.previous_button.clicked.connect(self.go_previous)
        self.save_button.clicked.connect(self.save_current)
        self.next_button.clicked.connect(self.save_and_next)
        self.skip_button.clicked.connect(self.go_next_without_save)
        self.export_button.clicked.connect(self.export_results)
        self.finish_button.clicked.connect(self.finish_and_reveal)

    def _image_path(self, filename: str) -> Path | None:
        direct = IMAGE_DIR / filename
        if direct.exists():
            return direct
        # Case-insensitive fallback for common Windows/Linux filename mismatches.
        try:
            target = filename.lower()
            for p in IMAGE_DIR.iterdir():
                if p.is_file() and p.name.lower() == target:
                    return p
        except FileNotFoundError:
            pass
        return None

    def _make_pixmap(self, path: Path) -> QPixmap:
        """Load an image and enlarge it by self.image_scale (224x224 -> 560x560 at 2.5x)."""
        with PILImage.open(path) as pil:
            pil = pil.convert("RGB")
            new_size = (
                max(1, int(round(pil.width * self.image_scale))),
                max(1, int(round(pil.height * self.image_scale))),
            )
            pil = pil.resize(new_size, PILImage.Resampling.LANCZOS)
            raw = pil.tobytes("raw", "RGB")
            qimg = QImage(raw, pil.width, pil.height, pil.width * 3, QImage.Format.Format_RGB888).copy()
            return QPixmap.fromImage(qimg)

    def _refresh_image(self, filename: str | None = None):
        filename = filename or self.filenames[self.index]
        side = int(224 * self.image_scale) + 20
        self.image_label.setMinimumSize(QSize(side, side))
        path = self.current_image_path
        if path:
            try:
                self.image_label.setPixmap(self._make_pixmap(path))
                self.image_label.setToolTip(str(path))
            except Exception as exc:
                self.image_label.setPixmap(QPixmap())
                self.image_label.setText(f"Could not load image:\n{path}\n{exc}")
        else:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText(
                f"Image not found:\n{IMAGE_DIR / filename}\n\n"
                "Check IMAGE_DIR in the configuration."
            )

    # ----- zoom -----------------------------------------------------------
    def _setup_zoom(self):
        def add(seq, fn):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(fn)

        for seq in ("Ctrl++", "Ctrl+=", "Ctrl+Plus"):
            add(seq, lambda: self.zoom_text(+1))
        for seq in ("Ctrl+-", "Ctrl+Minus"):
            add(seq, lambda: self.zoom_text(-1))
        for seq in ("Ctrl+Shift++", "Ctrl+Shift+=", "Ctrl+Shift+Plus"):
            add(seq, lambda: self.zoom_image(+1))
        for seq in ("Ctrl+Shift+-", "Ctrl+Shift+_", "Ctrl+Shift+Minus"):
            add(seq, lambda: self.zoom_image(-1))
        add("Ctrl+0", self.reset_zoom)

        # Catch Ctrl+wheel before child widgets (scroll areas / combo boxes) use it.
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            mods = event.modifiers()
            if mods & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta:
                    step = 1 if delta > 0 else -1
                    if mods & Qt.KeyboardModifier.ShiftModifier:
                        self.zoom_image(step)
                    else:
                        self.zoom_text(step)
                return True
        return super().eventFilter(obj, event)

    def zoom_text(self, direction: int):
        self.font_pt = max(FONT_MIN, min(FONT_MAX, self.font_pt + direction * FONT_STEP))
        self._apply_font()

    def zoom_image(self, direction: int):
        self.image_scale = max(IMAGE_SCALE_MIN, min(IMAGE_SCALE_MAX,
                               self.image_scale + direction * IMAGE_SCALE_STEP))
        self._refresh_image()

    def reset_zoom(self):
        self.font_pt = FONT_POINT_SIZE
        self.image_scale = IMAGE_SCALE
        self._apply_font()
        self._refresh_image()

    def _apply_font(self):
        app = QApplication.instance()
        font = app.font()
        font.setPointSize(self.font_pt)
        app.setFont(font)
        f = self.font_pt / BASE_FONT_FOR_LAYOUT
        self.progress_bar.setMinimumWidth(int(420 * f))
        self.progress_bar.setMinimumHeight(int(28 * f))
        for panel in self.candidate_panels.values():
            panel.apply_scale(f)

    def show_record(self):
        filename = self.filenames[self.index]
        canonical = self.records_by_model["6a"][filename]
        self.progress_label.setText(
            f"Image {self.index + 1} of {len(self.filenames)}  |  {filename}"
        )
        completed = sum(
            1 for fn in self.filenames
            if all(
                all(self.ratings.get(fn, {}).get(label, {}).get(k) in (1, 2, 3, 4, 5)
                    for k, *_ in CRITERIA)
                for label in ("A", "B", "C")
            )
        )
        self.progress_bar.setMaximum(max(1, len(self.filenames)))
        self.progress_bar.setValue(completed)
        self.progress_bar.setFormat(f"{completed}/{len(self.filenames)} images fully rated")

        scene_html = (
            f"<span style='color:{COL_MUTED}'>Filename</span> &nbsp;{html.escape(filename)}"
        )
        if canonical.get("scene"):
            scene_html += (
                f" &nbsp;&nbsp;&nbsp; <span style='color:{COL_MUTED}'>Scene</span> &nbsp;"
                f"{html.escape(str(canonical.get('scene', '')))}"
            )
        self.scene_label.setText(scene_html)

        self.current_image_path = self._image_path(filename)
        self._refresh_image(filename)

        refs = canonical.get("references", [])
        refs_html = "".join(
            f"<p style='margin:4px 0;'>"
            f"<span style='color:{COL_MUTED}'>{i + 1}.</span> "
            f"{html.escape(ref)}</p>"
            for i, ref in enumerate(refs)
        )
        self.references_label.setText(refs_html if refs else "(No reference captions found.)")

        mapping = self.blind_key[filename]
        saved = self.ratings.get(filename, {})
        for candidate_label, model in mapping.items():
            record = self.records_by_model[model][filename]
            panel = self.candidate_panels[candidate_label]
            panel.set_caption(record["prediction"])
            panel.set_scores(saved.get(candidate_label, {}))

        self.previous_button.setEnabled(self.index > 0)
        self.next_button.setText("Save & Next →" if self.index < len(self.filenames) - 1 else "Save")
        self.skip_button.setEnabled(self.index < len(self.filenames) - 1)

    def _current_scores(self) -> dict[str, dict[str, int | None]]:
        return {label: panel.get_scores() for label, panel in self.candidate_panels.items()}

    def _validate_current(self) -> tuple[bool, str]:
        scores = self._current_scores()
        missing = []
        for label in ("A", "B", "C"):
            for key, title, *_ in CRITERIA:
                if scores[label][key] not in (1, 2, 3, 4, 5):
                    missing.append(f"Candidate {label}: {title}")
        if missing:
            return False, "Please rate every criterion before saving:\n\n" + "\n".join(missing)
        return True, ""

    def save_current(self) -> bool:
        ok, message = self._validate_current()
        if not ok:
            QMessageBox.warning(self, "Incomplete ratings", message)
            return False

        filename = self.filenames[self.index]
        self.ratings[filename] = self._current_scores()
        self._write_json(self.ratings_path, self.ratings)
        self.show_record()
        return True

    def save_and_next(self):
        if self.save_current():
            if self.index < len(self.filenames) - 1:
                self.index += 1
                self.show_record()
            else:
                QMessageBox.information(self, "Evaluation", "Ratings saved. You are at the final image.")

    def go_previous(self):
        if self.index > 0:
            self.index -= 1
            self.show_record()

    def go_next_without_save(self):
        if self.index < len(self.filenames) - 1:
            answer = QMessageBox.question(
                self, "Skip without saving",
                "Move to the next image without saving the current ratings?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.index += 1
                self.show_record()

    def _score(self, scores: dict[str, Any]) -> float | None:
        vals = [scores.get(key) for key, *_ in CRITERIA]
        if not all(v in (1, 2, 3, 4, 5) for v in vals):
            return None
        return sum(weight * float(scores[key]) / 5.0 for key, _, weight, _ in CRITERIA) * 100.0

    def export_results(self):
        if not self.ratings:
            QMessageBox.information(self, "No ratings", "No ratings have been saved yet.")
            return
        out_csv = OUTPUT_DIR / "human_evaluation_scores.csv"
        out_json = OUTPUT_DIR / "human_evaluation_summary.json"
        rows = []
        per_model: dict[str, list[dict[str, Any]]] = {m: [] for m in ("6a", "6b", "6e")}
        for filename in self.filenames:
            saved = self.ratings.get(filename, {})
            mapping = self.blind_key.get(filename, {})
            for candidate_label in ("A", "B", "C"):
                model = mapping.get(candidate_label)
                if model not in per_model:
                    continue
                scores = saved.get(candidate_label, {})
                weighted = self._score(scores)
                row = {
                    "filename": filename,
                    "candidate": candidate_label,
                    "model": model,
                    **{key: scores.get(key) for key, *_ in CRITERIA},
                    "weighted_score_0_100": round(weighted, 3) if weighted is not None else None,
                }
                rows.append(row)
                per_model[model].append(row)

        fields = ["filename", "candidate", "model"] + [key for key, *_ in CRITERIA] + ["weighted_score_0_100"]
        with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        summary: dict[str, Any] = {
            "description": "Single-rater blinded human evaluation; weighted score is 0-100.",
            "criteria": [
                {"key": key, "name": name, "weight": weight}
                for key, name, weight, _ in CRITERIA
            ],
            "number_of_common_test_images": len(self.filenames),
            "models": {},
        }
        for model, model_rows in per_model.items():
            complete = [r for r in model_rows if r["weighted_score_0_100"] is not None]
            metric: dict[str, Any] = {
                "rated_images": len(complete),
                "mean_weighted_score_0_100": (
                    round(sum(r["weighted_score_0_100"] for r in complete) / len(complete), 4)
                    if complete else None
                ),
            }
            for key, *_ in CRITERIA:
                vals = [r[key] for r in model_rows if r[key] in (1, 2, 3, 4, 5)]
                metric[f"mean_{key}"] = round(sum(vals) / len(vals), 4) if vals else None
            summary["models"][model] = metric

        self._write_json(out_json, summary)
        QMessageBox.information(
            self, "Export complete",
            f"Saved results:\n{out_csv}\n{out_json}\n\n"
            "Note: the CSV includes model identities. Keep it private until evaluation is complete."
        )

    def finish_and_reveal(self):
        answer = QMessageBox.question(
            self, "Reveal model identities?",
            "This will export scored results with model identities. "
            "Use this only when you have finished blinded scoring.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.export_results()
            QMessageBox.information(
                self, "Model mapping",
                f"Blinded mapping is stored privately at:\n{self.blind_key_path}\n\n"
                "Candidate A/B/C assignments vary by image. The exported CSV maps each candidate "
                "to its model for analysis."
            )


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = app.font()
    font.setPointSize(FONT_POINT_SIZE)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet())
    try:
        window = HumanEvaluator()
    except Exception as exc:
        QMessageBox.critical(None, "Could not start evaluator", str(exc))
        raise
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()