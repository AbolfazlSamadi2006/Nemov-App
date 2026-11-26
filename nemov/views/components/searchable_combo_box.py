from PyQt6.QtWidgets import QComboBox, QCompleter, QStyledItemDelegate
from PyQt6.QtCore import Qt, QModelIndex

class CenteredItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index: QModelIndex):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter

class SearchableComboBox(QComboBox):
    """
    An enhanced QComboBox with:
    1. Center-aligned text and popup list items
    2. Live search autocomplete / filtering on typing (case-insensitive substring match)
    3. Proper synchronization of selected item and data
    4. Clean empty state with placeholder support
    """
    def __init__(self, parent=None, placeholder=""):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setItemDelegate(CenteredItemDelegate(self))

        le = self.lineEdit()
        if le:
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if placeholder:
                le.setPlaceholderText(placeholder)
            le.editingFinished.connect(self._on_editing_finished)
            le.returnPressed.connect(self._on_editing_finished)

        self.currentIndexChanged.connect(self._ensure_centered)
        self.currentTextChanged.connect(self._ensure_centered)

        comp = self.completer()
        if comp:
            comp.setFilterMode(Qt.MatchFlag.MatchContains)
            comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            comp.activated[str].connect(self._on_completer_activated)
            if comp.popup():
                comp.popup().setItemDelegate(CenteredItemDelegate(self))

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        normalized = (
            str(text)
            .replace("\u064a", "\u06cc")  # Arabic Yeh -> Persian Yeh
            .replace("\u0649", "\u06cc")  # Alef Maksura -> Persian Yeh
            .replace("\u0643", "\u06a9")  # Arabic Kaf -> Persian Kaf
            .replace("\u200c", " ")       # ZWNJ -> space
        )
        return " ".join(normalized.split()).lower()

    def _on_completer_activated(self, text: str):
        idx = self.find_normalized_index(text, allow_partial=False)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def find_normalized_index(self, text: str, allow_partial: bool = True) -> int:
        norm_query = self._normalize_text(text)
        if not norm_query:
            return -1
        for i in range(self.count()):
            if self._normalize_text(self.itemText(i)) == norm_query:
                return i
        if allow_partial:
            partial_matches = [
                i for i in range(self.count())
                if norm_query in self._normalize_text(self.itemText(i))
            ]
            if len(partial_matches) == 1:
                return partial_matches[0]
        return -1

    def resolve_current_data(self):
        """Returns valid itemData matching currentText even if user typed or edited manually."""
        norm_text = self._normalize_text(self.currentText())
        if not norm_text:
            self.setCurrentIndex(-1)
            return None
        cur_idx = self.currentIndex()
        if cur_idx >= 0 and self._normalize_text(self.itemText(cur_idx)) == norm_text:
            return self.itemData(cur_idx)
        idx = self.find_normalized_index(self.currentText(), allow_partial=True)
        if idx >= 0:
            self.setCurrentIndex(idx)
            return self.itemData(idx)
        self.setCurrentIndex(-1)
        return None

    def _ensure_centered(self, *args):
        le = self.lineEdit()
        if le:
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_empty(self):
        """Clears selection and lineEdit text so placeholder is visible."""
        self.setCurrentIndex(-1)
        if self.lineEdit():
            self.lineEdit().clear()
            self.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _on_editing_finished(self):
        text = self.currentText().strip()
        if not text:
            self.setCurrentIndex(-1)
            return
        idx = self.find_normalized_index(text, allow_partial=True)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(-1)
            self.setEditText(text)
