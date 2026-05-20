"""Generate the Python Basics track SQL + TypeScript runner config.

Run from repo root:

    python scripts/generate_python_basics.py

Writes two files:
- supabase/python_basics_seed.generated.sql  — inserts the track, modules, and 25 challenges
- apps/web/src/lib/python-basics-config.generated.ts  — CHALLENGE_CONFIG entries

The seed file is applied with `psql -f`; it uses ON CONFLICT DO UPDATE so re-running
is idempotent. The TS file is imported into `featured-files.ts` so the runner has
inline code/template/expected for each lesson.
"""

from __future__ import annotations

import json
import re
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
    n: int                 # 1..25
    module: int            # 1..7
    title: str
    scenario: str
    learner_goal: str
    instructions: str
    mode: str              # 'predict' or 'fillblank'
    # mode-specific payload:
    code: str = ""             # predict
    template: str = ""         # fillblank
    expected_stdout: str = ""
    prompt: str = ""           # predict only
    hint: str = ""             # fillblank only
    skills: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        kebab = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")
        return f"python-basics-{self.n:02d}-{kebab}"

    @property
    def uuid(self) -> str:
        # 0200..0218 for the 25 lessons
        return f"00000000-0000-0000-0000-{0x200 + (self.n - 1):012x}"


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


LESSONS: list[Lesson] = [
    # ---------------- Module 1 — First steps ----------------
    Lesson(
        n=1, module=1, title="Hello Python", mode="fillblank",
        scenario="Welcome to Python. The simplest way to make Python do something visible is to use `print()`.",
        learner_goal="Use `print()` to display text on screen.",
        instructions=(
            "Python has a built-in function called `print()`. It takes whatever you pass to it and shows it as output.\n\n"
            "```python\nprint(\"Hello, world!\")\n```\n\n"
            "The text inside quotes is called a **string**. Both single (`'`) and double (`\"`) quotes work the same way.\n\n"
            "Your turn: replace the `___` so the program prints exactly `hello, Python!`."
        ),
        template='___("hello, Python!")',
        expected_stdout="hello, Python!",
        hint="The function that shows text on screen.",
        skills=["python-basics", "io"],
    ),
    Lesson(
        n=2, module=1, title="Variables", mode="fillblank",
        scenario="Programs become useful when they remember things. Variables are how Python remembers values.",
        learner_goal="Assign a value to a variable and print it back.",
        instructions=(
            "A **variable** is a name that holds a value:\n\n"
            "```python\nname = \"Ada\"\nprint(name)  # Ada\n```\n\n"
            "Reading `name` later gives you back `\"Ada\"` — Python remembers it.\n\n"
            "Variable names should start with a letter, contain only letters/digits/underscores, "
            "and avoid Python reserved words like `print`, `if`, or `for`.\n\n"
            "Your turn: create a variable called `language` holding the string `\"Python\"`, then print it."
        ),
        template='___ = "Python"\nprint(language)',
        expected_stdout="Python",
        hint="The variable name on the left of `=` should match the name used in `print()`.",
        skills=["python-basics", "variables"],
    ),
    Lesson(
        n=3, module=1, title="Strings and f-strings", mode="fillblank",
        scenario="f-strings let you mix variables into text — far cleaner than gluing strings together with `+`.",
        learner_goal="Use an f-string to embed a variable inside text.",
        instructions=(
            "Two ways to combine text:\n\n"
            "```python\nname = \"Ada\"\n# Old way (works but clunky):\ngreeting = \"Hello, \" + name + \"!\"\n# f-string (clear):\ngreeting = f\"Hello, {name}!\"\nprint(greeting)\n```\n\n"
            "In an f-string, anything inside `{}` is evaluated as Python code and inserted.\n\n"
            "Your turn: build an f-string that prints `My favourite language is Python`."
        ),
        template='language = "Python"\nprint(f"My favourite language is {___}")',
        expected_stdout="My favourite language is Python",
        hint="What variable name did the line above define?",
        skills=["python-basics", "strings"],
    ),
    Lesson(
        n=4, module=1, title="Numbers and arithmetic", mode="predict",
        scenario="Python can do maths the way you'd expect. The operators are the standard ones plus a few extras.",
        learner_goal="Predict the output of an arithmetic expression.",
        instructions=(
            "Python supports:\n"
            "- `+` add, `-` subtract, `*` multiply\n"
            "- `/` divide (always returns a float)\n"
            "- `//` integer division (drops the remainder)\n"
            "- `%` modulo (the remainder)\n"
            "- `**` power\n\n"
            "```python\nprint(7 / 2)   # 3.5\nprint(7 // 2)  # 3\nprint(7 % 2)   # 1\nprint(2 ** 3)  # 8\n```\n\n"
            "What does this print? Remember: `*` happens before `+`, like in normal maths."
        ),
        code="print(10 + 3 * 2)",
        expected_stdout="16",
        prompt="What integer does this print?",
        skills=["python-basics", "arithmetic"],
    ),
    Lesson(
        n=5, module=1, title="Type conversion", mode="fillblank",
        scenario="Numbers entered by users often arrive as strings. Strings can't be added to numbers, so Python gives you `int()`, `float()`, and `str()` to convert.",
        learner_goal="Convert a string to an integer so you can do maths with it.",
        instructions=(
            "These all do different things:\n\n"
            "```python\nprint(2 + 3)         # 5  (number addition)\nprint(\"2\" + \"3\")     # 23 (string concatenation!)\nprint(int(\"2\") + 3)  # 5  (convert, then add)\n```\n\n"
            "`int(x)`, `float(x)`, and `str(x)` return a NEW value — they don't change `x`.\n\n"
            "Your turn: convert the string `\"42\"` to an integer and add 8."
        ),
        template='age_string = "42"\nage_in_eight_years = ___(age_string) + 8\nprint(age_in_eight_years)',
        expected_stdout="50",
        hint="The function that turns a string of digits into an integer.",
        skills=["python-basics", "types"],
    ),
    # ---------------- Module 2 — Making decisions ----------------
    Lesson(
        n=6, module=2, title="Booleans and comparisons", mode="predict",
        scenario="Decisions in code come down to 'yes' or 'no' — `True` or `False` in Python.",
        learner_goal="Predict whether a comparison is True or False.",
        instructions=(
            "Comparisons return a boolean:\n\n"
            "```python\nprint(5 > 3)    # True\nprint(5 == 5)   # True (note: == not =)\nprint(5 != 4)   # True (not equal)\nprint(5 < 3)    # False\nprint(5 >= 5)   # True\n```\n\n"
            "Common mistake: `=` is assignment (`x = 5`). `==` is comparison (`x == 5`).\n\n"
            "What does this print?"
        ),
        code="print(7 != 8)",
        expected_stdout="True",
        prompt="Is `7 != 8` True or False?",
        skills=["python-basics", "booleans"],
    ),
    Lesson(
        n=7, module=2, title="if elif else", mode="fillblank",
        scenario="When a condition is true, run one block of code; otherwise run another.",
        learner_goal="Write an if/else that picks one of two messages.",
        instructions=(
            "Basic shape:\n\n"
            "```python\nage = 18\nif age >= 18:\n    print(\"Adult\")\nelif age >= 13:\n    print(\"Teenager\")\nelse:\n    print(\"Kid\")\n```\n\n"
            "Notes:\n"
            "- The `:` at the end of the `if` line is required.\n"
            "- **Indentation matters.** Python uses indentation (4 spaces) to mark blocks.\n"
            "- `elif` is 'else if'. `else` catches everything else.\n\n"
            "Your turn: fill in the comparison so the program prints `cold`."
        ),
        template='temperature = 5\nif temperature ___ 10:\n    print("cold")\nelse:\n    print("warm")',
        expected_stdout="cold",
        hint="Pick the comparison operator that makes `5 _ 10` true.",
        skills=["python-basics", "control-flow"],
    ),
    Lesson(
        n=8, module=2, title="Logical operators", mode="predict",
        scenario="Real-world checks are usually combinations of smaller conditions.",
        learner_goal="Predict the result of a compound boolean expression.",
        instructions=(
            "Three operators for combining booleans:\n"
            "- `and` — both must be True\n"
            "- `or` — at least one must be True\n"
            "- `not` — flips True ↔ False\n\n"
            "```python\nprint(True and False)    # False\nprint(True or False)     # True\nprint(not True)          # False\nprint(5 > 3 and 5 < 10)  # True\n```\n\n"
            "Precedence: `not` > `and` > `or`. Use parens when unsure.\n\n"
            "What does this print?"
        ),
        code="print(10 > 5 or 10 > 100)",
        expected_stdout="True",
        prompt="Is at least one side True?",
        skills=["python-basics", "booleans"],
    ),
    # ---------------- Module 3 — Doing things many times ----------------
    Lesson(
        n=9, module=3, title="for loops with range", mode="fillblank",
        scenario="When you want to do something a known number of times, `for i in range(n)` is the idiomatic way.",
        learner_goal="Use a for loop with `range()` to print numbers.",
        instructions=(
            "```python\nfor i in range(5):\n    print(i)\n# prints 0, 1, 2, 3, 4 — NOT 5\n```\n\n"
            "`range(5)` produces 0, 1, 2, 3, 4. `range(2, 7)` produces 2, 3, 4, 5, 6 (starts at 2, stops BEFORE 7).\n\n"
            "Your turn: print the numbers 1 through 5 inclusive."
        ),
        template='for i in range(1, ___):\n    print(i)',
        expected_stdout="1\n2\n3\n4\n5",
        hint="`range(start, stop)` stops BEFORE `stop`, so what number do you put to include 5?",
        skills=["python-basics", "loops"],
    ),
    Lesson(
        n=10, module=3, title="for loops over lists", mode="fillblank",
        scenario="`for` can iterate over any sequence — lists, strings, dictionaries.",
        learner_goal="Iterate over a list and print each item.",
        instructions=(
            "```python\nfruits = [\"apple\", \"banana\", \"cherry\"]\nfor fruit in fruits:\n    print(fruit)\n```\n\n"
            "Each time through the loop, `fruit` takes the next value from the list.\n\n"
            "Your turn: iterate over the list and print each name."
        ),
        template='names = ["Ada", "Linus", "Grace"]\nfor ___ in names:\n    print(name)',
        expected_stdout="Ada\nLinus\nGrace",
        hint="The variable name in the `for` line should match the name used inside the loop.",
        skills=["python-basics", "loops", "lists"],
    ),
    Lesson(
        n=11, module=3, title="while loops", mode="fillblank",
        scenario="`while` loops run as long as a condition is true. Use them when you don't know in advance how many iterations you'll need.",
        learner_goal="Write a while loop that counts down.",
        instructions=(
            "```python\ncount = 3\nwhile count > 0:\n    print(count)\n    count = count - 1\nprint(\"Go!\")\n```\n\n"
            "The condition is checked at the **top** of each loop. If it's never made false, you have an infinite loop — Python won't stop on its own.\n\n"
            "Your turn: count down from 5 to 1, then print `Go!`."
        ),
        template='count = 5\nwhile count > 0:\n    print(count)\n    count = count ___ 1\nprint("Go!")',
        expected_stdout="5\n4\n3\n2\n1\nGo!",
        hint="Each iteration needs to make `count` smaller — which operator?",
        skills=["python-basics", "loops"],
    ),
    Lesson(
        n=12, module=3, title="break and continue", mode="predict",
        scenario="`break` exits a loop immediately. `continue` skips the rest of the current iteration and starts the next one.",
        learner_goal="Predict the output of a loop that breaks early.",
        instructions=(
            "```python\nfor i in range(10):\n    if i == 3:\n        break\n    print(i)\n# prints 0, 1, 2 (then breaks out)\n```\n\n"
            "```python\nfor i in range(5):\n    if i == 2:\n        continue\n    print(i)\n# prints 0, 1, 3, 4 (skips 2)\n```\n\n"
            "What does this print?"
        ),
        code="for i in range(5):\n    if i == 3:\n        break\n    print(i * 2)",
        expected_stdout="0\n2\n4",
        prompt="The loop breaks when `i == 3`. What does it print before that?",
        skills=["python-basics", "loops"],
    ),
    # ---------------- Module 4 — Collections ----------------
    Lesson(
        n=13, module=4, title="Lists", mode="fillblank",
        scenario="A list holds an ordered collection of values. Index from 0 to access them.",
        learner_goal="Index into a list to retrieve a specific item.",
        instructions=(
            "```python\ncolors = [\"red\", \"green\", \"blue\"]\nprint(colors[0])     # \"red\"\nprint(colors[2])     # \"blue\"\nprint(colors[-1])    # \"blue\" (last)\nprint(colors[1:3])   # [\"green\", \"blue\"] (slice)\n```\n\n"
            "Negative indices count from the end. Slices use `start:end` (end is exclusive).\n\n"
            "Your turn: print the second element of the list."
        ),
        template='scores = [95, 88, 76, 60]\nprint(scores[___])',
        expected_stdout="88",
        hint="The first element is at index 0, so the SECOND is at…?",
        skills=["python-basics", "lists"],
    ),
    Lesson(
        n=14, module=4, title="List operations", mode="fillblank",
        scenario="Lists are mutable. You can append, sort, and check membership.",
        learner_goal="Append to a list and check its length.",
        instructions=(
            "```python\nnumbers = [3, 1, 4]\nnumbers.append(1)        # add to end → [3, 1, 4, 1]\nprint(len(numbers))      # 4\nprint(2 in numbers)      # False\nprint(sorted(numbers))   # [1, 1, 3, 4] — new list\nnumbers.sort()           # sort in place\n```\n\n"
            "`append()` mutates the list. `sorted()` returns a new sorted list.\n\n"
            "Your turn: append `\"strawberry\"` to the list, then print its length."
        ),
        template='fruits = ["apple", "banana"]\nfruits.___("strawberry")\nprint(len(fruits))',
        expected_stdout="3",
        hint="The list method that adds an item to the end.",
        skills=["python-basics", "lists"],
    ),
    Lesson(
        n=15, module=4, title="Dictionaries", mode="fillblank",
        scenario="When you need to look something up by a label, use a dictionary.",
        learner_goal="Read a value from a dictionary by its key.",
        instructions=(
            "```python\nuser = {\"name\": \"Ada\", \"age\": 36, \"lang\": \"Python\"}\nprint(user[\"name\"])         # \"Ada\"\nuser[\"email\"] = \"ada@example.com\"  # add a key\nprint(len(user))            # 4\n```\n\n"
            "Keys are usually strings. Looking up a missing key raises `KeyError`.\n\n"
            "Your turn: print the value for the key `\"capital\"`."
        ),
        template='country = {"name": "France", "capital": "Paris", "population": 67}\nprint(country[___])',
        expected_stdout="Paris",
        hint="Use the key (as a string) inside square brackets.",
        skills=["python-basics", "dicts"],
    ),
    Lesson(
        n=16, module=4, title="Sets and tuples", mode="predict",
        scenario="`set` is unordered and de-duplicates. `tuple` is like a list but immutable.",
        learner_goal="Predict the size of a set after duplicates are removed.",
        instructions=(
            "```python\nunique = {1, 2, 2, 3, 3, 3}\nprint(unique)           # {1, 2, 3} — duplicates removed\n\npoint = (3, 4)\nprint(point[0])         # 3\n# point[0] = 99  → TypeError: tuples are immutable\n```\n\n"
            "Sets are great for 'is X in this collection?' — much faster than lists for big data.\n\n"
            "What does this print?"
        ),
        code="print(len({1, 2, 2, 2, 3}))",
        expected_stdout="3",
        prompt="Sets remove duplicates. How many unique values are there?",
        skills=["python-basics", "sets", "tuples"],
    ),
    # ---------------- Module 5 — Functions ----------------
    Lesson(
        n=17, module=5, title="Defining functions", mode="fillblank",
        scenario="Functions let you give a name to a block of code and reuse it.",
        learner_goal="Define a function and call it.",
        instructions=(
            "```python\ndef greet():\n    print(\"Hello!\")\n\ngreet()  # prints Hello!\ngreet()  # prints Hello! again\n```\n\n"
            "`def name():` defines; `name()` calls. The body is indented under `def`.\n\n"
            "Your turn: define a function `say_python` that prints `Python rocks`, then call it twice."
        ),
        template='def ___():\n    print("Python rocks")\n\nsay_python()\nsay_python()',
        expected_stdout="Python rocks\nPython rocks",
        hint="The function name in `def NAME():` should match the call below.",
        skills=["python-basics", "functions"],
    ),
    Lesson(
        n=18, module=5, title="Parameters", mode="fillblank",
        scenario="Functions become useful when they accept inputs and act on them.",
        learner_goal="Define a function with a parameter.",
        instructions=(
            "```python\ndef greet(name):\n    print(f\"Hello, {name}!\")\n\ngreet(\"Ada\")    # Hello, Ada!\ngreet(\"Linus\")  # Hello, Linus!\n```\n\n"
            "Default values let callers skip arguments:\n\n"
            "```python\ndef greet(name=\"friend\"):\n    print(f\"Hello, {name}!\")\n\ngreet()         # Hello, friend!\ngreet(\"Ada\")    # Hello, Ada!\n```\n\n"
            "Your turn: define a function that takes a name and prints `Welcome, <name>`."
        ),
        template='def welcome(___):\n    print(f"Welcome, {name}")\n\nwelcome("Grace")',
        expected_stdout="Welcome, Grace",
        hint="The parameter name in the parentheses should match the variable used inside the body.",
        skills=["python-basics", "functions"],
    ),
    Lesson(
        n=19, module=5, title="Return values", mode="fillblank",
        scenario="Most functions don't just print — they compute and return a value the caller uses.",
        learner_goal="Write a function that returns a value, then use the return value.",
        instructions=(
            "```python\ndef double(n):\n    return n * 2\n\nresult = double(7)\nprint(result)        # 14\nprint(double(3) + 1) # 7 (return values can be used in expressions)\n```\n\n"
            "`return` exits the function and sends the value back to the caller.\n\n"
            "Your turn: complete the function so it returns the sum of its two arguments."
        ),
        template='def add(a, b):\n    return ___\n\nprint(add(2, 3))\nprint(add(10, 20))',
        expected_stdout="5\n30",
        hint="The expression that adds two numbers — using the parameter names `a` and `b`.",
        skills=["python-basics", "functions"],
    ),
    Lesson(
        n=20, module=5, title="Local vs global scope", mode="predict",
        scenario="Variables defined inside a function don't exist outside it. This is called local scope.",
        learner_goal="Predict what gets printed given local vs global variables.",
        instructions=(
            "```python\nx = 10  # global\n\ndef show():\n    x = 20  # local — different variable!\n    print(x)\n\nshow()        # 20\nprint(x)      # 10 (global x unchanged)\n```\n\n"
            "Inside a function, assigning to a name creates a LOCAL variable. The global with the same name is hidden, not modified.\n\n"
            "What does this print?"
        ),
        code='count = 5\ndef add_one():\n    count = 100\n    print(count)\n\nadd_one()\nprint(count)',
        expected_stdout="100\n5",
        prompt="What does each `print` output, in order, separated by a newline?",
        skills=["python-basics", "functions", "scope"],
    ),
    # ---------------- Module 6 — Real code ----------------
    Lesson(
        n=21, module=6, title="try and except", mode="fillblank",
        scenario="Some operations can fail at runtime — dividing by zero, looking up a missing dict key. `try/except` lets you handle the failure instead of crashing.",
        learner_goal="Wrap a risky operation in try/except.",
        instructions=(
            "```python\ntry:\n    result = 10 / 0\nexcept ZeroDivisionError:\n    result = \"infinity\"\nprint(result)  # infinity\n```\n\n"
            "The `except` block runs only if the exception type matches. You can have multiple `except` blocks for different errors.\n\n"
            "Your turn: handle the missing-key case so the program prints `unknown` instead of crashing."
        ),
        template='user = {"name": "Ada"}\ntry:\n    email = user["email"]\n___ KeyError:\n    email = "unknown"\nprint(email)',
        expected_stdout="unknown",
        hint="The keyword that starts a fallback block when a `try` raises an error.",
        skills=["python-basics", "errors"],
    ),
    Lesson(
        n=22, module=6, title="List comprehensions", mode="fillblank",
        scenario="List comprehensions are Python's compact way to build a new list by transforming each item.",
        learner_goal="Use a list comprehension to build a list of squares.",
        instructions=(
            "```python\n# Long way:\nnumbers = [1, 2, 3, 4]\ndoubled = []\nfor n in numbers:\n    doubled.append(n * 2)\n# → [2, 4, 6, 8]\n\n# Comprehension:\ndoubled = [n * 2 for n in numbers]\n# → [2, 4, 6, 8]\n```\n\n"
            "Shape: `[expression for item in iterable]`. You can add an `if`: `[n for n in numbers if n > 2]`.\n\n"
            "Your turn: build a list of the squares of 1..5."
        ),
        template='squares = [n ___ 2 for n in range(1, 6)]\nprint(squares)',
        expected_stdout="[1, 4, 9, 16, 25]",
        hint="The power operator in Python is two characters.",
        skills=["python-basics", "comprehensions"],
    ),
    Lesson(
        n=23, module=6, title="Imports and the standard library", mode="fillblank",
        scenario="Python comes with batteries included — modules for math, dates, JSON, randomness, and more. You bring them in with `import`.",
        learner_goal="Import a module and use one of its values.",
        instructions=(
            "```python\nimport math\nprint(math.sqrt(16))    # 4.0\nprint(math.pi)          # 3.141592653589793\n\n# Or import a specific name:\nfrom math import sqrt\nprint(sqrt(25))         # 5.0\n```\n\n"
            "Other useful modules: `random`, `datetime`, `json`, `collections`.\n\n"
            "Your turn: import the math module and print the value of pi rounded to two decimals."
        ),
        template='___ math\nprint(round(math.pi, 2))',
        expected_stdout="3.14",
        hint="The keyword that pulls a module into your file.",
        skills=["python-basics", "imports"],
    ),
    # ---------------- Module 7 — Putting it together ----------------
    Lesson(
        n=24, module=7, title="Defining classes", mode="fillblank",
        scenario="Classes bundle data and behaviour together. They're the foundation of object-oriented Python.",
        learner_goal="Define a class with one attribute and one method.",
        instructions=(
            "```python\nclass Dog:\n    def __init__(self, name):\n        self.name = name\n\n    def bark(self):\n        print(f\"{self.name} says woof\")\n\nbuddy = Dog(\"Buddy\")\nbuddy.bark()    # Buddy says woof\n```\n\n"
            "`__init__` is the constructor — runs when you do `Dog(...)`. `self` is the instance the method is called on.\n\n"
            "Your turn: complete the constructor so the instance remembers its `name`."
        ),
        template='class Greeter:\n    def __init__(self, name):\n        self.___ = name\n\n    def greet(self):\n        print(f"Hello from {self.name}")\n\ng = Greeter("Python")\ng.greet()',
        expected_stdout="Hello from Python",
        hint="The attribute name on `self` should match what `greet()` reads as `self.name`.",
        skills=["python-basics", "classes"],
    ),
    Lesson(
        n=25, module=7, title="A tiny to-do list", mode="fillblank",
        scenario="Time to combine functions, lists, and dictionaries. You'll complete a small to-do list that adds tasks and prints them with their completion status.",
        learner_goal="Combine functions + lists + dicts to build a working to-do list.",
        instructions=(
            "You'll write the body of `add_task` so it appends a new task dictionary to the list.\n\n"
            "A task is a dictionary with keys `title` (string) and `done` (bool, defaults to False).\n\n"
            "Expected output:\n\n"
            "```\n- [ ] Learn Python\n- [x] Drink coffee\n- [ ] Write a function\n```"
        ),
        template=(
            'tasks = []\n\n'
            'def add_task(title, done=False):\n'
            '    tasks.___({"title": title, "done": done})\n\n'
            'def show_tasks():\n'
            '    for task in tasks:\n'
            '        mark = "x" if task["done"] else " "\n'
            '        print(f"- [{mark}] {task[\'title\']}")\n\n'
            'add_task("Learn Python")\n'
            'add_task("Drink coffee", done=True)\n'
            'add_task("Write a function")\n'
            'show_tasks()'
        ),
        expected_stdout="- [ ] Learn Python\n- [x] Drink coffee\n- [ ] Write a function",
        hint="The list method that adds an item to the end of a list (you used it back in lesson 14).",
        skills=["python-basics", "project"],
    ),
]


def sql_escape(text: str) -> str:
    """Escape a string for use inside a Postgres E'...' literal."""
    return text.replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n")


def write_sql() -> Path:
    lines: list[str] = []
    lines.append("-- AUTO-GENERATED by scripts/generate_python_basics.py")
    lines.append("-- Python Basics track: 1 track, 7 modules, 25 challenges.")
    lines.append("")

    # Track
    lines.append("insert into public.tracks (id, slug, title, description, difficulty, is_published)")
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

    # Modules
    for idx, mod in enumerate(MODULES):
        lines.append("insert into public.modules (id, track_id, slug, title, order_index)")
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

    # Challenges
    for lesson in LESSONS:
        module_index = lesson.module - 1
        m_uuid = module_uuid(MODULES[module_index].suffix)
        skills_array = "array[" + ", ".join(f"'{sql_escape(s)}'" for s in lesson.skills) + "]"
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
        lines.append(f"  E'{sql_escape(lesson.instructions)}',")
        lines.append("  null,")  # repo_template_url
        lines.append("  null,")  # repo_branch
        lines.append("  '{}',")
        lines.append("  '{\"max_hint_level\": 2, \"do_not_reveal_solution\": false, \"encourage_tests_first\": false}',")
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

    # Skills graph additions
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
    """Emit a TS module exporting the 25 entries as a partial CHALLENGE_CONFIG."""
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


if __name__ == "__main__":
    sql_path = write_sql()
    ts_path = write_ts()
    print(f"Wrote {sql_path.relative_to(ROOT)}")
    print(f"Wrote {ts_path.relative_to(ROOT)}")
