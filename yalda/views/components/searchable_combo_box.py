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

        self.currentIndexChanged.connect(self._ensure_centered)
        self.currentTextChanged.connect(self._ensure_centered)

        comp = self.completer()
        if comp:
            comp.setFilterMode(Qt.MatchFlag.MatchContains)
            comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            if comp.popup():
                comp.popup().setItemDelegate(CenteredItemDelegate(self))

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
        idx = self.findText(text, Qt.MatchFlag.MatchExactly)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            idx_c = self.findText(text, Qt.MatchFlag.MatchContains)
            if idx_c >= 0:
                self.setCurrentIndex(idx_c)
            else:
                self.setCurrentIndex(-1)
                self.setEditText(text)
