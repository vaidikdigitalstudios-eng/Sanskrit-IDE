
# Sanskrit IDE | Sanskrit Softwares
# Single-file Kivy application for .slp programs
# Designed for Android, tablets and desktop screens.

import ast
import operator
import re
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView


# ---------------- THEME ----------------

BG = "#F4F6FB"
WHITE = "#FFFFFF"
INK = "#20283A"
MUTED = "#7C879C"
ACCENT = "#6254E8"
BORDER = "#E2E6F0"
GREEN = "#16865B"
RED = "#C43E52"


def color(value):
    return get_color_from_hex(value)


# ---------------- INTERPRETER ----------------

class SanskritInterpreter:
    OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
    }

    def __init__(self):
        self.variables = {}
        self.constants = set()
        self.output = []

    def evaluate(self, expression):
        # Translate the language's inequality operator.
        expression = expression.replace("><", "!=")

        if "||" in expression:
            raise ValueError(
                "The || percentage operator needs a defined rule."
            )

        expression = re.sub(
            r"\btrue\b", "True", expression, flags=re.I
        )
        expression = re.sub(
            r"\bfalse\b", "False", expression, flags=re.I
        )

        return self._eval(ast.parse(expression, mode="eval").body)

    def _eval(self, node):
        if isinstance(node, ast.Constant):
            if type(node.value) in (int, float, str, bool):
                return node.value

        if isinstance(node, ast.Name):
            if node.id not in self.variables:
                raise ValueError(f"Unknown variable: {node.id}")
            return self.variables[node.id]

        if isinstance(node, ast.BinOp):
            operation = self.OPS.get(type(node.op))
            if operation is None:
                raise ValueError("Unsupported operator")
            return operation(
                self._eval(node.left), self._eval(node.right)
            )

        if isinstance(node, ast.UnaryOp):
            value = self._eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return +value
            if isinstance(node.op, ast.Not):
                return not value

        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, item in zip(node.ops, node.comparators):
                right = self._eval(item)
                operation = self.OPS.get(type(op))
                if operation is None or not operation(left, right):
                    return False
                left = right
            return True

        raise ValueError("Unsupported expression")

    def run(self, source):
        self.variables = {}
        self.constants = set()
        self.output = []

        # Extract integ main (self) { ... }
        match = re.search(
            r"\binteg\s+main\s*\(\s*self\s*\)\s*\{", source
        )

        if match:
            source = source[match.end():]
            depth = 1
            end = None

            for i, char in enumerate(source):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break

            if end is None:
                raise ValueError("Missing closing brace")
            source = source[:end]

        for number, raw in enumerate(source.splitlines(), 1):
            line = raw.strip()

            if not line or line.startswith("//"):
                continue

            if not line.endswith(";"):
                raise ValueError(f"Line {number}: add a semicolon")

            line = line[:-1].strip()

            # print("Hello");
            if line.startswith("print"):
                match = re.fullmatch(r"print\s*\((.*)\)", line)
                if not match:
                    raise ValueError(f"Line {number}: invalid print")

                self.output.append(
                    str(self.evaluate(match.group(1)))
                )
                continue

            # var Integ count = 10;
            # const Dec rate = 2.5;
            declaration = re.fullmatch(
                r"(var|const)\s+"
                r"(Integ|Dec|Bool|Flo|char)\s+"
                r"([A-Za-z_]\w*)\s*=\s*(.+)",
                line
            )

            if declaration:
                kind, typ, name, expr = declaration.groups()

                if name in self.variables:
                    raise ValueError(
                        f"Line {number}: '{name}' already exists"
                    )

                value = self.evaluate(expr)

                valid = {
                    "Integ": lambda v: type(v) is int,
                    "Dec": lambda v: type(v) in (int, float),
                    "Flo": lambda v: type(v) is float,
                    "Bool": lambda v: type(v) is bool,
                    "char": lambda v: (
                        isinstance(v, str) and len(v) == 1
                    ),
                }[typ]

                if not valid(value):
                    raise ValueError(
                        f"Line {number}: expected type {typ}"
                    )

                self.variables[name] = value
                if kind == "const":
                    self.constants.add(name)
                continue

            # Update a previously declared variable.
            assignment = re.fullmatch(
                r"([A-Za-z_]\w*)\s*=\s*(.+)", line
            )

            if assignment:
                name, expr = assignment.groups()

                if name not in self.variables:
                    raise ValueError(
                        f"Line {number}: unknown variable '{name}'"
                    )
                if name in self.constants:
                    raise ValueError(
                        f"Line {number}: cannot change constant '{name}'"
                    )

                self.variables[name] = self.evaluate(expr)
                continue

            raise ValueError(
                f"Line {number}: statement not implemented yet"
            )

        return "\n".join(self.output) or "Program finished."


# ---------------- REUSABLE UI ----------------

def make_button(text, callback, primary=False):
    button = Button(
        text=text,
        font_size="14sp",
        bold=primary,
        size_hint_y=None,
        height=dp(44),
        background_normal="",
        background_down="",
        background_color=color(ACCENT if primary else WHITE),
        color=color(WHITE if primary else INK)
    )
    button.bind(on_release=lambda *_: callback())
    return button


def make_label(text, size=12, fg=MUTED):
    return Label(
        text=text,
        font_size=f"{size}sp",
        color=color(fg),
        size_hint_y=None,
        height=dp(26),
        halign="left",
        valign="middle"
    )


# ---------------- IDE APPLICATION ----------------

class SanskritIDE(App):
    title = "Sanskrit IDE"

    def build(self):
        self.current_file = None

        Window.clearcolor = color(BG)

        self.root_box = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10)
        )

        # Header
        header = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(8)
        )

        brand = BoxLayout(orientation="vertical", spacing=0)
        brand.add_widget(Label(
            text="[b]Sanskrit IDE[/b]",
            markup=True,
            color=color(INK),
            font_size="22sp",
            halign="left"
        ))
        brand.add_widget(Label(
            text="Sanskrit Softwares  ·  .slp",
            color=color(MUTED),
            font_size="11sp",
            halign="left"
        ))
        header.add_widget(brand)

        self.status = Label(
            text="READY",
            color=color(GREEN),
            font_size="11sp",
            size_hint_x=None,
            width=dp(75)
        )
        header.add_widget(self.status)
        self.root_box.add_widget(header)

        # Toolbar: four touch-friendly buttons
        toolbar = GridLayout(
            cols=4,
            spacing=dp(7),
            size_hint_y=None,
            height=dp(44)
        )

        toolbar.add_widget(make_button("New", self.new_file))
        toolbar.add_widget(make_button("Open", self.open_file))
        toolbar.add_widget(make_button("Save", self.save_file))
        toolbar.add_widget(
            make_button("▶ Run", self.run_code, primary=True)
        )

        self.root_box.add_widget(toolbar)

        # Editor
        self.editor_panel = BoxLayout(
            orientation="vertical",
            spacing=dp(5)
        )
        self.editor_panel.add_widget(make_label("CODE EDITOR"))

        self.editor = TextInput(
            text=(
                'integ main (self) {\n'
                '    print("Hello from Sanskrit!");\n'
                '    var Integ number = 10;\n'
                '    print(number * 5);\n'
                '}\n'
            ),
            multiline=True,
            font_size="15sp",
            background_normal="",
            background_active="",
            background_color=color(WHITE),
            foreground_color=color(INK),
            cursor_color=color(ACCENT),
            selection_color=(0.39, 0.33, 0.91, 0.25),
            padding=[dp(12), dp(12)],
            size_hint=(1, 1)
        )
        self.editor_panel.add_widget(self.editor)

        # Output console
        self.output_panel = BoxLayout(
            orientation="vertical",
            spacing=dp(5)
        )
        self.output_panel.add_widget(make_label("OUTPUT CONSOLE"))

        self.console = TextInput(
            text="Your program output will appear here.",
            readonly=True,
            multiline=True,
            font_size="13sp",
            background_normal="",
            background_active="",
            background_color=color(WHITE),
            foreground_color=color(INK),
            padding=[dp(12), dp(10)],
            size_hint=(1, 1)
        )
        self.output_panel.add_widget(self.console)

        # Workspace switches between vertical and horizontal.
        self.workspace = BoxLayout(
            orientation="vertical",
            spacing=dp(10)
        )
        self.workspace.add_widget(self.editor_panel)
        self.workspace.add_widget(self.output_panel)
        self.root_box.add_widget(self.workspace)

        self.root_box.add_widget(make_label(
            "Devloped by Sanskrit Softwares For more information contact at info@sanskritsoftwares.isroot.in",
            10
        ))

        # Adapt the workspace whenever the available width changes.
        self.root_box.bind(size=self.adapt_layout)
        Clock.schedule_once(self.adapt_layout, 0)

        return self.root_box

    def adapt_layout(self, *_):
        if not hasattr(self, "workspace"):
            return

        width = self.root_box.width

        if width >= dp(760):
            self.workspace.orientation = "horizontal"
            self.editor_panel.size_hint = (0.66, 1)
            self.output_panel.size_hint = (0.34, 1)
        else:
            self.workspace.orientation = "vertical"
            self.editor_panel.size_hint = (1, 0.68)
            self.output_panel.size_hint = (1, 0.32)

    def show_message(self, title, message):
        content = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10)
        )
        content.add_widget(Label(
            text=message,
            color=color(INK),
            halign="left",
            valign="middle"
        ))
        content.add_widget(make_button(
            "Close", lambda: popup.dismiss(), primary=True
        ))

        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.88, 0.42)
        )
        popup.open()

    def new_file(self):
        self.editor.text = ""
        self.console.text = "New .slp file"
        self.current_file = None
        self.status.text = "NEW FILE"

    def file_picker(self, save=False):
        chooser = FileChooserListView(
            path=str(Path.home()),
            filters=["*.slp"]
        )

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(8)
        )
        layout.add_widget(chooser)

        filename = TextInput(
            text="program.slp",
            multiline=False,
            size_hint_y=None,
            height=dp(42)
        )

        if save:
            layout.add_widget(filename)

        popup = Popup(
            title="Save .slp" if save else "Open .slp",
            content=layout,
            size_hint=(0.94, 0.88)
        )

        def confirm():
            try:
                if save:
                    name = Path(
                        filename.text or "program.slp"
                    ).name
                    if not name.endswith(".slp"):
                        name += ".slp"
                    path = Path(chooser.path) / name
                    path.write_text(
                        self.editor.text, encoding="utf-8"
                    )
                    self.current_file = path
                    self.status.text = "SAVED"
                else:
                    if not chooser.selection:
                        return
                    path = Path(chooser.selection[0])
                    self.editor.text = path.read_text(
                        encoding="utf-8"
                    )
                    self.current_file = path
                    self.status.text = "OPENED"

                popup.dismiss()

            except Exception as exc:
                self.show_message("File error", str(exc))

        layout.add_widget(make_button(
            "Save" if save else "Open", confirm, primary=True
        ))
        popup.open()

    def open_file(self):
        self.file_picker(save=False)

    def save_file(self):
        if self.current_file:
            try:
                self.current_file.write_text(
                    self.editor.text, encoding="utf-8"
                )
                self.status.text = "SAVED"
            except Exception as exc:
                self.show_message("Save error", str(exc))
        else:
            self.file_picker(save=True)

    def run_code(self):
        try:
            result = SanskritInterpreter().run(self.editor.text)
            self.console.text = result
            self.status.text = "SUCCESS"
        except Exception as exc:
            self.console.text = f"Error:\n{exc}"
            self.status.text = "ERROR"


if __name__ == "__main__":
    try:
        SanskritIDE().run()
    except Exception as error:
        print("Sanskrit IDE startup error:", repr(error))
        raise
