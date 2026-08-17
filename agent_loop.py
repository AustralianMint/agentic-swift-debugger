import subprocess
from anthropic import Anthropic

client = Anthropic()  # reads ANTHROPIC_API_KEY from your environment automatically

# Where your Swift package lives — change this if your folder name differs
SWIFT_PROJECT_DIR = "."

# --- Step 1: the actual functions the agent is allowed to call ---
# These are normal Python functions. Nothing magic happens here yet —
# Claude can't run these directly, it can only ASK us to run them.

def list_files(path: str = ".") -> str:
    """Lists files and folders inside a given directory, relative to the project root."""
    import os
    IGNORE_DIRS = {"venv", ".git", ".build", "__pycache__", ".swiftpm", ".vscode"}
    entries = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            entries.append(os.path.join(root, f))
    return "\n".join(entries) if entries else "No files found."

def read_file(path: str) -> str:
    """Reads a file and returns its text content."""
    with open(path, "r") as f:
        return f.read()


def write_file(path: str, contents: str) -> str:
    """Overwrites a file with new content."""
    with open(path, "w") as f:
        f.write(contents)
    return f"Wrote {len(contents)} characters to {path}"


def run_build() -> str:
    """Runs `swift build` inside the project folder and returns the output."""
    result = subprocess.run(
        ["swift", "build"],
        cwd=SWIFT_PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return output if output.strip() else "Build succeeded, no output."


def run_tests() -> str:
    """Runs `swift test` inside the project folder and returns the output."""
    result = subprocess.run(
        ["swift", "test"],
        cwd=SWIFT_PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return output if output.strip() else "Tests passed, no output."


# A lookup table so we can call the right Python function by name once
# Claude tells us which tool it wants.
TOOL_FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "run_build": run_build,
    "run_tests": run_tests,
}

# --- Step 2: describe those functions to Claude ---
# This is the "menu" Claude sees. It only knows the name, description,
# and what inputs each tool takes — never the actual code inside.

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at a given path, relative to the Swift project root.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Overwrite a file at a given path with new contents, relative to the Swift project root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "contents": {"type": "string"},
            },
            "required": ["path", "contents"],
        },
    },
    {
        "name": "run_build",
        "description": "Run `swift build` and return any compiler output or errors.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_tests",
        "description": "Run `swift test` and return the test results.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
    "name": "list_files",
    "description": "List all files in a directory (recursively), relative to the project root. Use this first to discover what files exist before reading them.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directory to list, defaults to project root."}},
        "required": [],
        },
    },
]


# --- Step 3: the loop ---
# We keep sending messages back and forth until Claude stops asking for tools
# and gives a final text answer instead.

def run_agent(task: str):
    messages = [{"role": "user", "content": task}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=2000,
            tools=TOOLS,
            messages=messages,
        )

        # Claude's reply becomes the next message in the conversation history
        messages.append({"role": "assistant", "content": response.content})

        # If Claude didn't ask for a tool, it's done — print the final answer
        if response.stop_reason != "tool_use":
            for block in response.content:
                if block.type == "text":
                    print("\n[Claude]:", block.text)
            break

        # Otherwise, find the tool call(s), actually run them, and report back
        tool_results = []
        for block in response.content:
            if block.type == "text":
                print("\n[Claude]:", block.text)
            elif block.type == "tool_use":
                print(f"\n[Tool call] {block.name}({block.input})")
                func = TOOL_FUNCTIONS[block.name]
                result = func(**block.input)
                print(f"[Tool result] {result[:300]}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        # Send the tool results back so Claude can decide what to do next
        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    run_agent(
        "The Swift package has a failing test. Read the source file and the "
        "test file, figure out what's missing, fix the source file, and "
        "re-run the tests to confirm it passes."
    )