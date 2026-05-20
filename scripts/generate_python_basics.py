"""Generate the Python Basics track SQL + TypeScript runner config.

Run from repo root:

    python scripts/generate_python_basics.py

Writes two files:
- supabase/python_basics_seed.generated.sql  — inserts the track, modules, and 25 challenges
- apps/web/src/lib/python-basics-config.generated.ts  — CHALLENGE_CONFIG entries

Each lesson follows a strict 4-part template so they're uniform across the
track (60–80 words target):

    **Concept.** One or two sentences in plain English.

    **Example.**

    ```python
    short_example()
    ```

    **Your turn.** One sentence telling the learner what to type.
    (predict-mode lessons replace this with "Predict the output of:")

    **Expected.** `<single-line expected output>`

The seed file is idempotent (ON CONFLICT DO UPDATE); the TS file is imported
into featured-files.ts.
"""

from __future__ import annotations

import json
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACK_UUID = "00000000-0000-0000-0000-000000000002"


@dataclass
class Module:
    suffix: int  # last hex chunk in the module UUID
    title: str


@dataclass
class Lesson:
    n: int
    module: int
    title: str
    scenario: str
    learner_goal: str
    mode: str  # 'predict' or 'fillblank'
    # Structured instruction fields (replace the freeform `instructions` string).
    concept: str
    example_code: str  # multi-line is fine; we wrap in ```python```
    your_turn: str  # for fillblank: "Replace ___ so it prints X"; for predict: "Predict the output."
    # Mode-specific payload:
    code: str = ""              # predict only — the snippet shown
    template: str = ""          # fillblank only — Monaco's initial content
    expected_stdout: str = ""
    prompt: str = ""            # predict only — input label
    hint: str = ""              # fillblank only
    skills: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        kebab = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")
        return f"python-basics-{self.n:02d}-{kebab}"

    @property
    def uuid(self) -> str:
        return f"00000000-0000-0000-0000-{0x200 + (self.n - 1):012x}"

    def instructions(self) -> str:
        """Assemble the markdown instructions from the structured fields.
        Same template for every lesson; only the `Your turn` wording differs
        between predict and fillblank modes."""
        lines = [f"**Concept.** {self.concept.strip()}", "", "**Example.**", ""]
        lines.append("```python")
        lines.append(self.example_code.strip("\n"))
        lines.append("```")
        lines.append("")
        if self.mode == "predict":
            lines.append(f"**Predict.** {self.your_turn.strip()}")
        else:
            lines.append(f"**Your turn.** {self.your_turn.strip()}")
        lines.append("")
        expected_one_line = self.expected_stdout.replace("\n", " · ")
        lines.append(f"**Expected.** `{expected_one_line}`")
        return "\n".join(lines)


MODULES: list[Module] = [
    Module(0x20, "Module 1 — First steps"),
    Module(0x21, "Module 2 — Making decisions"),
    Module(0x22, "Module 3 — Doing things many times"),
    Module(0x23, "Module 4 — Collections"),
    Module(0x24, "Module 5 — Functions"),
    Module(0x25, "Module 6 — Real code"),
    Module(0x26, "Module 7 — Putting it together"),
]


def module_uuid(suffix: int) -> str:
    return f"00000000-0000-0000-0000-{suffix:012x}"


def module_slug(idx: int) -> str:
    titles = [
        "first-steps",
        "making-decisions",
        "doing-things-many-times",
        "collections",
        "functions",
        "real-code",
        "putting-it-together",
    ]
    return f"python-basics-{titles[idx]}"


# fmt: off
LESSONS: list[Lesson] = [
    # ============ Module 1 — First steps ============
    Lesson(
        n=1, module=1, title="Hello Python", mode="fillblank",
        scenario="The simplest way to make Python do something visible is to call `print()`.",
        learner_goal="Use `print()` to display text.",
        concept="`print()` is a built-in function. Whatever you pass to it appears as output. Text in quotes is a **string**; single (`'`) or double (`\"`) both work.",
        example_code='print("Hello, world!")',
        your_turn="Replace `___` so the program prints `hello, Python!`.",
        template='___("hello, Python!")',
        expected_stdout="hello, Python!",
        hint="The function that shows text on screen.",
        skills=["python-basics", "io"],
    ),
    Lesson(
        n=2, module=1, title="Variables", mode="fillblank",
        scenario="Programs are useful when they remember things. A variable is how Python remembers a value.",
        learner_goal="Assign a value to a variable and print it back.",
        concept="`name = value` stores `value` under the name `name`. Reading the name later gives you back the value. Names use letters/digits/underscores and avoid Python keywords like `print`.",
        example_code='name = "Ada"\nprint(name)  # Ada',
        your_turn="Create a variable called `language` holding `\"Python\"`, then print it.",
        template='___ = "Python"\nprint(language)',
        expected_stdout="Python",
        hint="The name on the left of `=` should match the one in `print()`.",
        skills=["python-basics", "variables"],
    ),
    Lesson(
        n=3, module=1, title="Strings and f-strings", mode="fillblank",
        scenario="f-strings drop variables into text cleanly, without gluing strings with `+`.",
        learner_goal="Use an f-string to embed a variable in text.",
        concept="An f-string is a string prefixed with `f`. Anything inside `{}` is evaluated as Python and inserted: `f\"Hello, {name}!\"` becomes `\"Hello, Ada!\"` when `name = \"Ada\"`.",
        example_code='name = "Ada"\nprint(f"Hello, {name}!")  # Hello, Ada!',
        your_turn="Fill in `___` so the output is `My favourite language is Python`.",
        template='language = "Python"\nprint(f"My favourite language is {___}")',
        expected_stdout="My favourite language is Python",
        hint="The variable defined on the line above.",
        skills=["python-basics", "strings"],
    ),
    Lesson(
        n=4, module=1, title="Numbers and arithmetic", mode="predict",
        scenario="Python supports the standard arithmetic operators plus a couple of extras.",
        learner_goal="Predict the output of an arithmetic expression.",
        concept="`+ - * /` work as expected. `/` always returns a float. `//` is integer division (drops the remainder). `%` is the remainder. `**` is power. `*` happens before `+`, like normal maths.",
        example_code="print(7 / 2)   # 3.5\nprint(7 // 2)  # 3\nprint(7 % 2)   # 1\nprint(2 ** 3)  # 8",
        your_turn="What does this print?",
        code="print(10 + 3 * 2)",
        expected_stdout="16",
        prompt="What integer does this print?",
        skills=["python-basics", "arithmetic"],
    ),
    Lesson(
        n=5, module=1, title="Type conversion", mode="fillblank",
        scenario="Numbers from users often arrive as strings — and strings won't add to numbers without converting.",
        learner_goal="Convert a string to an int so you can do maths with it.",
        concept="`int(x)`, `float(x)`, and `str(x)` return a NEW value of that type; they don't change `x`. `int(\"2\") + 3` is `5`, but `\"2\" + \"3\"` is `\"23\"`.",
        example_code='print(2 + 3)         # 5  (number addition)\nprint("2" + "3")     # 23 (string concatenation!)\nprint(int("2") + 3)  # 5',
        your_turn="Convert the string `\"42\"` to an integer and add 8.",
        template='age_string = "42"\nage_in_eight_years = ___(age_string) + 8\nprint(age_in_eight_years)',
        expected_stdout="50",
        hint="The function that turns a string of digits into an integer.",
        skills=["python-basics", "types"],
    ),
    # ============ Module 2 — Making decisions ============
    Lesson(
        n=6, module=2, title="Booleans and comparisons", mode="predict",
        scenario="Decisions in code come down to `True` or `False`.",
        learner_goal="Predict whether a comparison is True or False.",
        concept="Comparisons return a boolean: `>` `<` `>=` `<=` `==` `!=`. Common mistake: `=` is assignment, `==` is comparison.",
        example_code="print(5 > 3)    # True\nprint(5 == 5)   # True\nprint(5 != 4)   # True\nprint(5 < 3)    # False",
        your_turn="What does this print?",
        code="print(7 != 8)",
        expected_stdout="True",
        prompt="Is `7 != 8` True or False?",
        skills=["python-basics", "booleans"],
    ),
    Lesson(
        n=7, module=2, title="if elif else", mode="fillblank",
        scenario="`if` runs a block when a condition is true; `else` runs when it isn't.",
        learner_goal="Pick one of two messages based on a comparison.",
        concept="`if condition:` followed by an indented block. `elif` is \"else if\". `else` catches everything else. The `:` is required, and indentation (4 spaces) marks the block.",
        example_code='age = 18\nif age >= 18:\n    print("Adult")\nelse:\n    print("Kid")',
        your_turn="Fill in the comparison so the program prints `cold`.",
        template='temperature = 5\nif temperature ___ 10:\n    print("cold")\nelse:\n    print("warm")',
        expected_stdout="cold",
        hint="Pick the comparison operator that makes `5 _ 10` true.",
        skills=["python-basics", "control-flow"],
    ),
    Lesson(
        n=8, module=2, title="Logical operators", mode="predict",
        scenario="Real conditions are usually combinations of smaller ones.",
        learner_goal="Predict the result of a compound boolean expression.",
        concept="`and` — both sides must be true. `or` — at least one. `not` — flips True/False. Precedence: `not` > `and` > `or`; use parens when unsure.",
        example_code="print(True and False)    # False\nprint(True or False)     # True\nprint(5 > 3 and 5 < 10)  # True",
        your_turn="What does this print?",
        code="print(10 > 5 or 10 > 100)",
        expected_stdout="True",
        prompt="Is at least one side True?",
        skills=["python-basics", "booleans"],
    ),
    # ============ Module 3 — Doing things many times ============
    Lesson(
        n=9, module=3, title="for loops with range", mode="fillblank",
        scenario="When you want to do something a fixed number of times, `for i in range(n)` is idiomatic.",
        learner_goal="Use a `for` loop with `range()` to print numbers.",
        concept="`range(n)` produces 0, 1, … n-1. `range(a, b)` produces a, a+1, … b-1 — it stops BEFORE `b`.",
        example_code="for i in range(5):\n    print(i)\n# prints 0, 1, 2, 3, 4 (not 5)",
        your_turn="Print the numbers 1 through 5 inclusive.",
        template="for i in range(1, ___):\n    print(i)",
        expected_stdout="1\n2\n3\n4\n5",
        hint="`range(start, stop)` stops BEFORE `stop`. What includes 5?",
        skills=["python-basics", "loops"],
    ),
    Lesson(
        n=10, module=3, title="for loops over lists", mode="fillblank",
        scenario="`for` walks over any sequence — lists, strings, dictionaries — one item at a time.",
        learner_goal="Iterate over a list and print each item.",
        concept="`for item in iterable:` binds `item` to each element in turn. The loop variable's name is yours to choose; it should describe one element.",
        example_code='fruits = ["apple", "banana", "cherry"]\nfor fruit in fruits:\n    print(fruit)',
        your_turn="Fill in the loop variable so each name prints.",
        template='names = ["Ada", "Linus", "Grace"]\nfor ___ in names:\n    print(name)',
        expected_stdout="Ada\nLinus\nGrace",
        hint="The variable in `for ___ in names:` must match the one in `print(...)`.",
        skills=["python-basics", "loops", "lists"],
    ),
    Lesson(
        n=11, module=3, title="while loops", mode="fillblank",
        scenario="`while` runs as long as a condition is true. Use it when you don't know in advance how many iterations.",
        learner_goal="Count down from 5 with a `while` loop.",
        concept="The condition is checked at the TOP of each iteration. The loop must eventually make the condition false — otherwise it runs forever (the sandbox aborts at 200,000 steps with a clear error).",
        example_code='count = 3\nwhile count > 0:\n    print(count)\n    count = count - 1\nprint("Go!")',
        your_turn="Fill in the operator so `count` shrinks each iteration.",
        template='count = 5\nwhile count > 0:\n    print(count)\n    count = count ___ 1\nprint("Go!")',
        expected_stdout="5\n4\n3\n2\n1\nGo!",
        hint="Each iteration must make `count` smaller.",
        skills=["python-basics", "loops"],
    ),
    Lesson(
        n=12, module=3, title="break and continue", mode="predict",
        scenario="`break` exits a loop immediately. `continue` skips to the next iteration.",
        learner_goal="Predict the output of a loop that breaks early.",
        concept="`break` jumps out of the enclosing loop right away — no more iterations. `continue` jumps back to the loop header for the next iteration, skipping the rest of the body.",
        example_code="for i in range(5):\n    if i == 2:\n        continue   # skips 2\n    print(i)",
        your_turn="What does this print?",
        code="for i in range(5):\n    if i == 3:\n        break\n    print(i * 2)",
        expected_stdout="0\n2\n4",
        prompt="The loop breaks when `i == 3`. What does it print before that?",
        skills=["python-basics", "loops"],
    ),
    # ============ Module 4 — Collections ============
    Lesson(
        n=13, module=4, title="Lists", mode="fillblank",
        scenario="A list holds an ordered collection of values. Index from 0 to access them.",
        learner_goal="Read a specific element of a list by its index.",
        concept="`my_list[0]` is the first element. `my_list[-1]` is the last. `my_list[a:b]` is a slice from index `a` (inclusive) to `b` (exclusive).",
        example_code='colors = ["red", "green", "blue"]\nprint(colors[0])     # "red"\nprint(colors[-1])    # "blue"',
        your_turn="Print the second element of `scores`.",
        template="scores = [95, 88, 76, 60]\nprint(scores[___])",
        expected_stdout="88",
        hint="Indexes start at 0. The second element is at…?",
        skills=["python-basics", "lists"],
    ),
    Lesson(
        n=14, module=4, title="List operations", mode="fillblank",
        scenario="Lists are mutable: you can grow them, sort them, and check what's in them.",
        learner_goal="Append to a list and check its length.",
        concept="`my_list.append(x)` adds `x` to the end (in-place). `len(my_list)` returns how many elements it has. `x in my_list` checks membership.",
        example_code='numbers = [3, 1, 4]\nnumbers.append(1)\nprint(len(numbers))  # 4',
        your_turn="Append `\"strawberry\"` to `fruits`, then print its length.",
        template='fruits = ["apple", "banana"]\nfruits.___("strawberry")\nprint(len(fruits))',
        expected_stdout="3",
        hint="The list method that adds an item to the end.",
        skills=["python-basics", "lists"],
    ),
    Lesson(
        n=15, module=4, title="Dictionaries", mode="fillblank",
        scenario="A dictionary maps keys to values — like a real-world index card.",
        learner_goal="Read a value from a dictionary by its key.",
        concept="`my_dict[key]` retrieves the value stored under `key`. Keys are usually strings. Looking up a missing key raises `KeyError`.",
        example_code='user = {"name": "Ada", "age": 36}\nprint(user["name"])  # Ada',
        your_turn="Print the value for the key `\"capital\"`.",
        template='country = {"name": "France", "capital": "Paris", "population": 67}\nprint(country[___])',
        expected_stdout="Paris",
        hint="Use the key — as a string — inside the square brackets.",
        skills=["python-basics", "dicts"],
    ),
    Lesson(
        n=16, module=4, title="Sets and tuples", mode="predict",
        scenario="A `set` is unordered and de-duplicates. A `tuple` is like a list but immutable.",
        learner_goal="Predict how many unique values are in a set.",
        concept="`{1, 2, 2, 3}` becomes `{1, 2, 3}` — duplicates are removed. Sets are fast for membership checks. Tuples use `(...)`; their elements can't change.",
        example_code="unique = {1, 2, 2, 3, 3, 3}\nprint(unique)  # {1, 2, 3}",
        your_turn="What does this print?",
        code="print(len({1, 2, 2, 2, 3}))",
        expected_stdout="3",
        prompt="How many unique values are in the set?",
        skills=["python-basics", "sets", "tuples"],
    ),
    # ============ Module 5 — Functions ============
    Lesson(
        n=17, module=5, title="Defining functions", mode="fillblank",
        scenario="Functions give a name to a block of code so you can reuse it.",
        learner_goal="Define a function with `def` and call it.",
        concept="`def name():` defines a function. The body is indented under it. `name()` calls it — and you can call it as many times as you like.",
        example_code='def greet():\n    print("Hello!")\n\ngreet()\ngreet()',
        your_turn="Define `say_python` so calling it prints `Python rocks`, then call it twice.",
        template='def ___():\n    print("Python rocks")\n\nsay_python()\nsay_python()',
        expected_stdout="Python rocks\nPython rocks",
        hint="The name in `def NAME():` must match the call below.",
        skills=["python-basics", "functions"],
    ),
    Lesson(
        n=18, module=5, title="Parameters", mode="fillblank",
        scenario="Functions become useful when they take inputs.",
        learner_goal="Define a function with one parameter.",
        concept="`def greet(name):` — `name` is a parameter. Inside the body it holds whatever value the caller passes. Defaults work too: `def greet(name=\"friend\"):`.",
        example_code='def greet(name):\n    print(f"Hello, {name}!")\n\ngreet("Ada")    # Hello, Ada!',
        your_turn="Add the parameter `name` so the function prints `Welcome, Grace`.",
        template='def welcome(___):\n    print(f"Welcome, {name}")\n\nwelcome("Grace")',
        expected_stdout="Welcome, Grace",
        hint="The parameter name in `(...)` must match what's used inside the body.",
        skills=["python-basics", "functions"],
    ),
    Lesson(
        n=19, module=5, title="Return values", mode="fillblank",
        scenario="Most functions don't just print — they compute and return a value the caller uses.",
        learner_goal="Write a function that returns its result.",
        concept="`return expr` exits the function and sends `expr` back to the caller. The caller can store it (`x = f()`) or use it in an expression (`f() + 1`).",
        example_code="def double(n):\n    return n * 2\n\nresult = double(7)\nprint(result)  # 14",
        your_turn="Fill in the return expression so `add(a, b)` returns their sum.",
        template="def add(a, b):\n    return ___\n\nprint(add(2, 3))\nprint(add(10, 20))",
        expected_stdout="5\n30",
        hint="The expression that adds the two parameters.",
        skills=["python-basics", "functions"],
    ),
    Lesson(
        n=20, module=5, title="Local vs global scope", mode="predict",
        scenario="Variables defined inside a function don't exist outside it — that's local scope.",
        learner_goal="Predict what each `print` outputs.",
        concept="Assigning to a name inside a function creates a LOCAL variable. The global with the same name is hidden, not modified. The outer global keeps its old value when the function returns.",
        example_code="x = 10\ndef show():\n    x = 20  # local — different variable\n    print(x)\n\nshow()      # 20\nprint(x)    # 10",
        your_turn="What does this print, one number per line?",
        code="count = 5\ndef add_one():\n    count = 100\n    print(count)\n\nadd_one()\nprint(count)",
        expected_stdout="100\n5",
        prompt="One number per line, in order.",
        skills=["python-basics", "functions", "scope"],
    ),
    # ============ Module 6 — Real code ============
    Lesson(
        n=21, module=6, title="try and except", mode="fillblank",
        scenario="Some operations fail at runtime (dividing by zero, missing dict keys). `try/except` lets you handle the failure.",
        learner_goal="Catch a `KeyError` so the program prints `unknown`.",
        concept="`try:` runs its block. If an exception of a matching type is raised, control jumps to the matching `except`. The `except` keyword introduces the fallback.",
        example_code='try:\n    result = 10 / 0\nexcept ZeroDivisionError:\n    result = "infinity"\nprint(result)  # infinity',
        your_turn="Replace `___` with the keyword that starts the fallback block.",
        template='user = {"name": "Ada"}\ntry:\n    email = user["email"]\n___ KeyError:\n    email = "unknown"\nprint(email)',
        expected_stdout="unknown",
        hint="The keyword that starts a fallback block after `try`.",
        skills=["python-basics", "errors"],
    ),
    Lesson(
        n=22, module=6, title="List comprehensions", mode="fillblank",
        scenario="List comprehensions build a new list by transforming each item — in one line.",
        learner_goal="Build a list of the squares of 1..5.",
        concept="The shape is `[expr for item in iterable]`. You can add an `if`: `[n for n in nums if n > 0]`. It's a compact replacement for a `for`-loop + `.append()` pattern.",
        example_code="numbers = [1, 2, 3, 4]\ndoubled = [n * 2 for n in numbers]\nprint(doubled)  # [2, 4, 6, 8]",
        your_turn="Fill in the operator so the comprehension produces squares.",
        template="squares = [n ___ 2 for n in range(1, 6)]\nprint(squares)",
        expected_stdout="[1, 4, 9, 16, 25]",
        hint="The power operator in Python is two characters.",
        skills=["python-basics", "comprehensions"],
    ),
    Lesson(
        n=23, module=6, title="Imports and the standard library", mode="fillblank",
        scenario="Python comes with batteries included — `import` pulls a module in.",
        learner_goal="Import `math` and use one of its values.",
        concept="`import math` makes the module available as `math`. Reach into it with a dot: `math.pi`, `math.sqrt(16)`. `from math import sqrt` imports just one name.",
        example_code="import math\nprint(math.sqrt(16))  # 4.0\nprint(math.pi)        # 3.141592653589793",
        your_turn="Add the keyword that pulls `math` into the program.",
        template="___ math\nprint(round(math.pi, 2))",
        expected_stdout="3.14",
        hint="The keyword that brings a module into your file.",
        skills=["python-basics", "imports"],
    ),
    # ============ Module 7 — Putting it together ============
    Lesson(
        n=24, module=7, title="Defining classes", mode="fillblank",
        scenario="Classes bundle data and behaviour together — the foundation of object-oriented Python.",
        learner_goal="Complete a class's constructor.",
        concept="`__init__` is the constructor; it runs when you do `MyClass(...)`. `self` is the instance the method is called on. Attributes assigned to `self.x` are stored on the instance.",
        example_code='class Dog:\n    def __init__(self, name):\n        self.name = name\n    def bark(self):\n        print(f"{self.name} says woof")',
        your_turn="Set `self.name = name` so `greet()` reads `self.name` correctly.",
        template='class Greeter:\n    def __init__(self, name):\n        self.___ = name\n    def greet(self):\n        print(f"Hello from {self.name}")\n\ng = Greeter("Python")\ng.greet()',
        expected_stdout="Hello from Python",
        hint="The attribute name on `self` must match what `greet()` reads.",
        skills=["python-basics", "classes"],
    ),
    Lesson(
        n=25, module=7, title="A tiny to-do list", mode="fillblank",
        scenario="Combine functions, lists, and dictionaries into a tiny to-do list.",
        learner_goal="Make `add_task` actually add a task to the list.",
        concept="A task is a dict with keys `title` and `done`. `add_task(title, done=False)` should append a new dict to the global `tasks` list. The list method `.append(item)` adds `item` to the end.",
        example_code='tasks = []\ntasks.append({"title": "Learn Python", "done": False})\nprint(tasks[0]["title"])  # Learn Python',
        your_turn="Replace `___` with the list method that adds an item to the end.",
        template=(
            "tasks = []\n\n"
            "def add_task(title, done=False):\n"
            "    tasks.___({\"title\": title, \"done\": done})\n\n"
            "def show_tasks():\n"
            "    for task in tasks:\n"
            "        mark = \"x\" if task[\"done\"] else \" \"\n"
            "        print(f\"- [{mark}] {task['title']}\")\n\n"
            'add_task("Learn Python")\n'
            'add_task("Drink coffee", done=True)\n'
            'add_task("Write a function")\n'
            "show_tasks()"
        ),
        expected_stdout="- [ ] Learn Python\n- [x] Drink coffee\n- [ ] Write a function",
        hint="The same list method you used back in lesson 14.",
        skills=["python-basics", "project"],
    ),
]
# fmt: on


def sql_escape(text: str) -> str:
    """Escape for use inside a Postgres E'...' literal."""
    return text.replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n")


def write_sql() -> Path:
    lines: list[str] = []
    lines.append("-- AUTO-GENERATED by scripts/generate_python_basics.py")
    lines.append("-- Python Basics track: 1 track, 7 modules, 25 challenges.")
    lines.append("")
    lines.append(
        "insert into public.tracks (id, slug, title, description, difficulty, is_published)"
    )
    lines.append("values (")
    lines.append(f"  '{TRACK_UUID}',")
    lines.append("  'python-basics',")
    lines.append("  E'Python Basics',")
    lines.append(
        "  E'Your first 25 lessons in Python — variables, conditionals, loops, functions, classes. "
        "Step-by-step exercises that run entirely in your browser. No prior coding experience required.',"
    )
    lines.append("  'beginner',")
    lines.append("  true")
    lines.append(")")
    lines.append("on conflict (slug) do update set")
    lines.append("  title = excluded.title,")
    lines.append("  description = excluded.description,")
    lines.append("  difficulty = excluded.difficulty,")
    lines.append("  is_published = excluded.is_published;")
    lines.append("")
    for idx, mod in enumerate(MODULES):
        lines.append(
            "insert into public.modules (id, track_id, slug, title, order_index)"
        )
        lines.append("values (")
        lines.append(f"  '{module_uuid(mod.suffix)}',")
        lines.append(f"  '{TRACK_UUID}',")
        lines.append(f"  '{module_slug(idx)}',")
        lines.append(f"  E'{sql_escape(mod.title)}',")
        lines.append(f"  {idx + 1}")
        lines.append(")")
        lines.append("on conflict (track_id, slug) do update set")
        lines.append("  title = excluded.title,")
        lines.append("  order_index = excluded.order_index;")
        lines.append("")

    for lesson in LESSONS:
        module_index = lesson.module - 1
        m_uuid = module_uuid(MODULES[module_index].suffix)
        skills_array = (
            "array[" + ", ".join(f"'{sql_escape(s)}'" for s in lesson.skills) + "]"
        )
        lines.append(
            "insert into public.challenges (\n"
            "  id, module_id, slug, title, scenario, learner_goal, instructions,\n"
            "  repo_template_url, repo_branch, validation_config_json, ai_rules_json,\n"
            "  skills, is_free, order_index\n"
            ") values ("
        )
        lines.append(f"  '{lesson.uuid}',")
        lines.append(f"  '{m_uuid}',")
        lines.append(f"  '{lesson.slug}',")
        lines.append(f"  E'{sql_escape(lesson.title)}',")
        lines.append(f"  E'{sql_escape(lesson.scenario)}',")
        lines.append(f"  E'{sql_escape(lesson.learner_goal)}',")
        lines.append(f"  E'{sql_escape(lesson.instructions())}',")
        lines.append("  null,")
        lines.append("  null,")
        lines.append("  '{}',")
        lines.append(
            "  '{\"max_hint_level\": 2, \"do_not_reveal_solution\": false, \"encourage_tests_first\": false}',"
        )
        lines.append(f"  {skills_array},")
        lines.append("  true,")
        lines.append(f"  {lesson.n}")
        lines.append(")")
        lines.append("on conflict (slug) do update set")
        lines.append(
            "  module_id = excluded.module_id,\n"
            "  title = excluded.title,\n"
            "  scenario = excluded.scenario,\n"
            "  learner_goal = excluded.learner_goal,\n"
            "  instructions = excluded.instructions,\n"
            "  repo_template_url = excluded.repo_template_url,\n"
            "  repo_branch = excluded.repo_branch,\n"
            "  validation_config_json = excluded.validation_config_json,\n"
            "  ai_rules_json = excluded.ai_rules_json,\n"
            "  skills = excluded.skills,\n"
            "  is_free = excluded.is_free,\n"
            "  order_index = excluded.order_index;"
        )
        lines.append("")

    used_skills = sorted({s for lesson in LESSONS for s in lesson.skills})
    titles = {
        "python-basics": "Python basics",
        "io": "Input / output",
        "variables": "Variables",
        "strings": "Strings",
        "arithmetic": "Arithmetic",
        "types": "Type conversion",
        "booleans": "Booleans",
        "control-flow": "Control flow",
        "loops": "Loops",
        "lists": "Lists",
        "dicts": "Dictionaries",
        "sets": "Sets",
        "tuples": "Tuples",
        "functions": "Functions",
        "scope": "Variable scope",
        "errors": "Error handling",
        "comprehensions": "Comprehensions",
        "imports": "Imports",
        "classes": "Classes",
        "project": "Mini-project",
    }
    lines.append("insert into public.skills (slug, name) values")
    rows = [f"  ('{s}', '{sql_escape(titles.get(s, s.title()))}')" for s in used_skills]
    lines.append(",\n".join(rows))
    lines.append("on conflict (slug) do update set name = excluded.name;")
    lines.append("")

    out_path = ROOT / "supabase" / "python_basics_seed.generated.sql"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_ts() -> Path:
    entries: list[str] = []
    for lesson in LESSONS:
        if lesson.mode == "predict":
            payload = {
                "mode": "predict",
                "code": lesson.code,
                "expected_stdout": lesson.expected_stdout,
            }
            if lesson.prompt:
                payload["prompt"] = lesson.prompt
        elif lesson.mode == "fillblank":
            payload = {
                "mode": "fillblank",
                "template": lesson.template,
                "expected_stdout": lesson.expected_stdout,
            }
            if lesson.hint:
                payload["hint"] = lesson.hint
        else:
            raise ValueError(f"Unknown mode: {lesson.mode}")
        entries.append(f"  {json.dumps(lesson.slug)}: {json.dumps(payload, indent=2)},")

    body = (
        "// AUTO-GENERATED by scripts/generate_python_basics.py\n"
        "// Inline runner config for the 25 Python Basics lessons.\n\n"
        'import type { ChallengeRunnerConfig } from "@/lib/featured-files";\n\n'
        "export const PYTHON_BASICS_CONFIG: Record<string, ChallengeRunnerConfig> = {\n"
        + "\n".join(entries)
        + "\n};\n"
    )
    out_path = ROOT / "apps" / "web" / "src" / "lib" / "python-basics-config.generated.ts"
    out_path.write_text(body, encoding="utf-8")
    return out_path


def word_count_report() -> None:
    """Print word counts so we can see distribution at a glance."""
    print("\nInstruction word counts:")
    for lesson in LESSONS:
        text = lesson.instructions()
        wc = len(text.split())
        print(f"  {lesson.slug}: {wc} words")


if __name__ == "__main__":
    sql_path = write_sql()
    ts_path = write_ts()
    print(f"Wrote {sql_path.relative_to(ROOT)}")
    print(f"Wrote {ts_path.relative_to(ROOT)}")
    word_count_report()
    # Unused import: textwrap is here in case we want to dedent example_code later.
    _ = textwrap
