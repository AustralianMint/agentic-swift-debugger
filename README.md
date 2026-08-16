# agentic-swift-debugger

A small tool-calling agent (via the Anthropic API) that operates on a real Swift package. It reads, writes to files, runs `swift build` and `swift run`, and runs tests.
The aim is for me to learn how an LLM agent behaves when given a constrained set of tools over a real codebase, rather than only producing text.

## What it is concretely

Instead of me manually pasting code into a chat window to debug something, this project gives Cluade direct hands ona Swift project. It reads files, edits them, and verifies its own changes by running the actual build and test commands. `agent_loop.py` drives the loop.

## Project Structure

- `Sources/AgentTarget/` — the Swift package the agent operates on
- `Tests/AgentTargetTests/` — its test suite
- `agent_loop.py` — the Python agent: tool definitions + the request/response loop

## Setup

\`\`\`bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install anthropic
export ANTHROPIC_API_KEY="your-key-here"
python3 agent_loop.py
\`\`\`

Requires the Swift toolchain (`swift build` / `swift test`) available on your PATH.
