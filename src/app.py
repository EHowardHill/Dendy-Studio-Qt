import sys
import os
import re
import subprocess
import shutil
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPlainTextEdit,
    QSplitter,
    QAction,
    QFileDialog,
    QStatusBar,
    QLabel,
    QToolBar,
    QDialog,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QInputDialog,
)
from PyQt5.QtGui import (
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QTextOption,
    QPainter,
    QTextFormat,
    QPixmap,
    QIcon,  # Added for app icon
)
from PyQt5.QtCore import Qt, QRegExp, QRect, QSize, pyqtSlot


# LineNumberArea class (unchanged)
class LineNumberArea(QLabel):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet(
            "background-color: #f0f0f0; color: #606060; padding-left: 8px;"
        )
        self.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.setTextFormat(Qt.PlainText)
        self.setMargin(0)
        self.setContentsMargins(8, 0, 0, 0)

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


# extract_raylib_identifiers function (unchanged)
def extract_raylib_identifiers(header_path):
    with open(header_path, "r", encoding="utf-8") as f:
        content = f.read()
    function_pattern = r"RLAPI \w+ (\w+)\("
    functions = re.findall(function_pattern, content)
    macro_pattern = r"#define (\w+)"
    macros = re.findall(macro_pattern, content)
    return functions, macros


# CppHighlighter class (unchanged)
class CppHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, raylib_functions, raylib_macros):
        super().__init__(parent)
        self.highlighting_rules = []
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#0000FF"))
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#800080"))
        self.macro_format = QTextCharFormat()
        self.macro_format.setForeground(QColor("#008000"))
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#008000"))
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#FF0000"))
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#FF8000"))

        keywords = [
            "int",
            "void",
            "if",
            "else",
            "while",
            "for",
            "return",
            "class",
            "struct",
            "enum",
            "typedef",
            "const",
            "static",
            "volatile",
            "public",
            "private",
            "protected",
            "friend",
            "virtual",
            "template",
            "typename",
            "namespace",
            "using",
            "bool",
            "true",
            "false",
            "float",
            "double",
            "long",
            "short",
            "signed",
            "unsigned",
            "auto",
            "break",
            "case",
            "continue",
            "default",
            "do",
            "goto",
            "switch",
            "this",
            "throw",
            "try",
            "catch",
        ]
        keyword_pattern = r"\b(" + "|".join(keywords) + r")\b"
        self.highlighting_rules.append((QRegExp(keyword_pattern), self.keyword_format))

        function_pattern = r"\b(" + "|".join(raylib_functions) + r")\b"
        self.highlighting_rules.append(
            (QRegExp(function_pattern), self.function_format)
        )

        macro_pattern = r"\b(" + "|".join(raylib_macros) + r")\b"
        self.highlighting_rules.append((QRegExp(macro_pattern), self.macro_format))

        number_pattern = r"\b\d+\b"
        self.highlighting_rules.append((QRegExp(number_pattern), self.number_format))

        string_pattern = r'"[^"]*"|\'[^\']*\''
        self.highlighting_rules.append((QRegExp(string_pattern), self.string_format))

        comment_pattern = r"//.*"
        self.highlighting_rules.append((QRegExp(comment_pattern), self.comment_format))

        self.multiline_comment_start = QRegExp(r"/\*")
        self.multiline_comment_end = QRegExp(r"\*/")

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = self.multiline_comment_start.indexIn(text)
        while start_index >= 0:
            end_index = self.multiline_comment_end.indexIn(text, start_index)
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = (
                    end_index - start_index + self.multiline_comment_end.matchedLength()
                )
            self.setFormat(start_index, comment_length, self.comment_format)
            start_index = self.multiline_comment_start.indexIn(
                text, start_index + comment_length
            )


# CodeEditor class (unchanged)
class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 10))
        self.setTabStopWidth(4 * self.fontMetrics().width(" "))
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)
        self.current_file = None

    def line_number_area_width(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count //= 10
            digits += 1
        space = 3 + self.fontMetrics().width("9") * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#606060"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


# MainWindow class with modifications
class MainWindow(QMainWindow):
    def __init__(self, raylib_functions, raylib_macros):
        super().__init__()
        self.setWindowTitle("Dendy Studio")
        self.setGeometry(100, 100, 900, 700)
        self.setWindowIcon(QIcon("icon.png"))  # Added app icon

        self.code_editor = CodeEditor(self)
        self.code_editor.setStyleSheet("background-color: white; color: black;")

        self.console = QPlainTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 10))
        self.console.setStyleSheet("background-color: black; color: white;")

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.code_editor)
        splitter.addWidget(self.console)
        splitter.setSizes([500, 200])
        self.setCentralWidget(splitter)

        self.highlighter = CppHighlighter(
            self.code_editor.document(), raylib_functions, raylib_macros
        )

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.create_toolbar()

        self.current_file = None
        self.project_dir = None
        self.setStyleSheet("QMainWindow { background-color: white; }")

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        create_action = QAction("Create", self)
        create_action.triggered.connect(self.create_project)
        toolbar.addAction(create_action)

        load_action = QAction("Load", self)
        load_action.triggered.connect(self.load_file)
        toolbar.addAction(load_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        save_action.setShortcut("Ctrl+S")  # Added Ctrl + S shortcut
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        run_action = QAction("Run", self)
        run_action.triggered.connect(self.run_code)
        toolbar.addAction(run_action)

        toolbar.addSeparator()

        publish_action = QAction("Publish", self)
        publish_action.triggered.connect(self.publish_project)
        toolbar.addAction(publish_action)

        help_action = QAction("Help", self)  # Added Help button
        help_action.triggered.connect(self.show_help_dialog)
        toolbar.addAction(help_action)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open C++ File", "", "C++ Files (*.cpp *.h);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.code_editor.setPlainText(f.read())
                self.code_editor.current_file = file_path
                self.project_dir = os.path.dirname(file_path)
                self.status_bar.showMessage(f"Loaded: {file_path}")
            except Exception as e:
                self.status_bar.showMessage(f"Error loading file: {str(e)}")

    def save_file(self):
        if not self.code_editor.current_file:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save C++ File", "", "C++ Files (*.cpp *.h);;All Files (*)"
            )
            if not file_path:
                return
            self.code_editor.current_file = file_path

        try:
            with open(self.code_editor.current_file, "w", encoding="utf-8") as f:
                f.write(self.code_editor.toPlainText())
            self.status_bar.showMessage(f"Saved: {self.code_editor.current_file}")
        except Exception as e:
            self.status_bar.showMessage(f"Error saving file: {str(e)}")

    def run_code(self):
        self.status_bar.showMessage("Compilation started...")
        self.console.clear()

        code = self.code_editor.toPlainText()

        if not os.path.exists("temp"):
            os.makedirs("temp")
        with open(os.path.join("temp", "main.cpp"), "w", encoding="utf-8") as f:
            f.write(code)

        self.status_bar.showMessage("Compiling...")
        process = subprocess.Popen(
            [
                "zig\\zig.exe",
                "c++",
                "temp\\main.cpp",
                "-o",
                "temp\\main.exe",
                "-Iraylib/include",
                "-Lraylib/lib",
                "-lraylib",
                "-lopengl32",
                "-lgdi32",
                "-lwinmm",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        stdout, stderr = process.communicate()
        if stdout:
            self.console.appendPlainText("--- Compilation Output ---\n" + stdout)
        if stderr:
            self.console.appendPlainText("--- Compilation Errors ---\n" + stderr)

        if process.returncode != 0:
            self.status_bar.showMessage("Compilation failed")
            self.console.appendPlainText(
                "\nCompilation failed with return code: " + str(process.returncode)
            )
        else:
            self.status_bar.showMessage("Compilation successful, running program...")
            self.console.appendPlainText("\n--- Program Output ---")

            run_process = subprocess.Popen(
                ["temp\\main.exe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            stdout, stderr = run_process.communicate()
            if stdout:
                self.console.appendPlainText(stdout)
            if stderr:
                self.console.appendPlainText("--- Program Errors ---\n" + stderr)

            if run_process.returncode == 0:
                self.status_bar.showMessage("Program completed successfully")
            else:
                self.status_bar.showMessage(
                    f"Program exited with code: {run_process.returncode}"
                )


def create_project(self):
    project_name, ok = QInputDialog.getText(self, "Create New Project", "Project Name:")

    if not ok or not project_name:
        return

    project_dir = os.path.join(os.getcwd(), "projects", project_name)
    try:
        os.makedirs(project_dir, exist_ok=True)

        main_cpp_path = os.path.join(project_dir, "main.cpp")
        default_code = """#include "raylib.h"

int main() {
    const int screenWidth = 800;
    const int screenHeight = 450;
    
    InitWindow(screenWidth, screenHeight, "Dendy Project");
    SetTargetFPS(60);
    
    while (!WindowShouldClose()) {
        BeginDrawing();
        ClearBackground(RAYWHITE);
        DrawText("Hello, sheep! Hello, cup of tea!", 190, 200, 20, LIGHTGRAY);
        EndDrawing();
    }
    
    CloseWindow();
    
    return 0;
}
"""
        with open(main_cpp_path, "w", encoding="utf-8") as f:
            f.write(default_code)

        self.project_dir = project_dir
        self.code_editor.current_file = main_cpp_path
        with open(main_cpp_path, "r", encoding="utf-8") as f:
            self.code_editor.setPlainText(f.read())

        self.status_bar.showMessage(f"Created new project: {project_name}")
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")


def publish_project(self):
    if not self.project_dir:
        QMessageBox.warning(
            self,
            "Warning",
            "No active project to publish. Please create or load a project first.",
        )
        return

    base_dir = QFileDialog.getExistingDirectory(
        self,
        "Select Project Location",
        os.path.expanduser("~"),
        QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
    )

    if not base_dir:
        return

    # Combine base directory with the new directory name
    project_name = os.path.basename(self.project_dir)
    publish_dir = os.path.join(base_dir, project_name)

    try:

        # Create the new directory
        os.makedirs(publish_dir, exist_ok=True)
        print(f"Created new directory: {publish_dir}")

        # You can still append your project name logic if needed        
        self.save_file()
        self.status_bar.showMessage("Building executable for publishing...")
        self.console.appendPlainText("Building executable for publishing...")

        exe_path = os.path.join(os.getcwd(), "main.exe")

        compile_process = subprocess.Popen(
            [
                "zig\\zig.exe",
                "c++",
                self.code_editor.current_file,
                "-o",
                exe_path,
                "-Iraylib/include",
                "-Lraylib/lib",
                "-lraylib",
                "-lopengl32",
                "-lgdi32",
                "-lwinmm"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        stdout, stderr = compile_process.communicate()
        if stdout:
            self.console.appendPlainText(stdout)
        if stderr:
            self.console.appendPlainText(stderr)

        if compile_process.returncode != 0:
            self.status_bar.showMessage("Failed to build executable")
            self.console.appendPlainText("Failed to build executable")
            return

        publish_exe_path = os.path.join(publish_dir, f"{project_name}.exe")
        shutil.copy2(exe_path, publish_exe_path)

        raylib_dll = os.path.join("raylib", "lib", "raylib.dll")
        if os.path.exists(raylib_dll):
            shutil.copy2(raylib_dll, publish_dir)

        with open(os.path.join(publish_dir, "README.txt"), "w") as f:
            f.write(f"{project_name}\n\n")
            f.write("Created with Dendy Studio\n\n")
            f.write(f"Run {project_name}.exe to start the application.")

        self.status_bar.showMessage(f"Project published to: {publish_dir}")
        self.console.appendPlainText(
            f"Project successfully published to: {publish_dir}"
        )

        QMessageBox.information(
            self, "Success", f"Project published to:\n{publish_dir}"
        )
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to publish project: {str(e)}")


def show_help_dialog(self):
    dialog = QDialog(self)
    dialog.setWindowTitle("Help")

    layout = QVBoxLayout()

    title_label = QLabel("About Dendy Studio")
    title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
    layout.addWidget(title_label)

    desc_label = QLabel(
        "Dendy Studio is a code editor for simple games, made with Raylib.\nFrom Cinemint, with love!"
    )
    layout.addWidget(desc_label)

    link_label = QLabel(
        '<a href="https://cinemint.online">https://cinemint.online</a>'
    )
    link_label.setOpenExternalLinks(True)
    layout.addWidget(link_label)

    close_button = QPushButton("Close")
    close_button.clicked.connect(dialog.accept)
    layout.addWidget(close_button)

    dialog.setLayout(layout)
    dialog.exec_()


# Add methods to MainWindow class
MainWindow.create_project = create_project
MainWindow.publish_project = publish_project
MainWindow.show_help_dialog = show_help_dialog  # Added Help method

# Main execution (unchanged)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    header_path = os.path.join("raylib", "include", "raylib.h")
    functions, macros = extract_raylib_identifiers(header_path)
    main_window = MainWindow(functions, macros)
    main_window.show()
    sys.exit(app.exec_())
