# Agent Architecture

This document describes the agent orchestration system used for journal automation.

## Overview

The journal automation system uses a multi-agent architecture to generate, validate, and commit journal entries automatically. Each agent has a specific responsibility and they coordinate through a central orchestrator.

## Agents

### 1. Git Analysis Agent (`agents/git_analysis.py`)

**Responsibility:** Analyzes git repositories to extract commit data and project activity.

**Key Functions:**
- Scans configured directories for git repositories
- Extracts commit messages, authors, and timestamps
- Identifies work patterns and productivity metrics
- Generates structured commit data for content generation

**Input:** Repository paths, configuration settings
**Output:** List of commits and activity summaries

### 2. Content Generation Agent (`agents/content_generation.py`)

**Responsibility:** Generates natural language journal entries from structured git data.

**Key Functions:**
- Transforms commit logs into readable summaries
- Categorizes work by project and activity type
- Generates daily and monthly summaries
- Maintains consistent tone and formatting

**Input:** Structured git data, date range
**Output:** Markdown-formatted journal entries

### 3. Fact Checking Agent (`agents/fact_checking.py`)

**Responsibility:** Validates generated content against actual data.

**Key Functions:**
- Cross-references generated summaries with git data
- Ensures commit counts are accurate
- Verifies project names and descriptions
- Flags inconsistencies for review

**Input:** Generated content, git data
**Output:** Validation report with any discrepancies

### 4. Quality Assurance Agent (`agents/quality_assurance.py`)

**Responsibility:** Ensures output meets quality standards and formatting requirements.

**Key Functions:**
- Validates markdown formatting
- Checks for completeness and consistency
- Enforces journal entry structure
- Scores content quality

**Input:** Generated journal entries
**Output:** Quality score and improvement suggestions

### 5. Validator Agent (`agents/validator.py`)

**Responsibility:** Performs final validation before committing entries.

**Key Functions:**
- Checks for missing sections or incomplete entries
- Verifies links and references
- Ensures proper file naming and organization
- Validates against entry templates

**Input:** Journal entry files
**Output:** Validation result and approval status

### 6. Orchestrator (`agents/orchestrator.py`)

**Responsibility:** Coordinates all agents and manages the workflow.

**Key Functions:**
- Executes agents in the correct sequence
- Manages parallel execution where applicable
- Handles agent errors and retries
- Maintains state and progress tracking
- Manages human approval flow

**Input:** Date, configuration
**Output:** Final journal entry and commit status

## Workflow

The standard workflow is:

1. **Git Analysis** → Extract commit data
2. **Content Generation** → Create draft entry
3. **Fact Checking** → Validate accuracy
4. **Quality Assurance** → Ensure quality standards
5. **Validator** → Final verification
6. **Commit** → (if approved) Commit to repository

### Parallel Execution

Certain agents can run in parallel when configured:
- Fact Checking can run alongside Content Generation for partial validation
- Quality Assurance and Validator can work on different aspects simultaneously

## Configuration

Agent behavior is configured through `config.py`:

```python
{
    "quality": {
        "min_commits_for_section": 3,
        "require_human_approval": False,
        "parallel_agents": True,
        "commit_as_they_go": True,
    }
}
```

### Key Settings

- `min_commits_for_section`: Minimum commits to create a dedicated project section
- `require_human_approval`: If True, pauses for human review before committing
- `parallel_agents`: Enables parallel execution where supported
- `commit_as_they_go`: Commits immediately after approval vs. batching

## Error Handling

Each agent implements retry logic:

```python
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
```

Agents report errors to the orchestrator, which:
1. Logs the error
2. Attempts retry if retry count < MAX_RETRIES
3. Escalates to manual review if retries exhausted
4. Preserves partial state for recovery

## Human in the Loop

When `require_human_approval` is True:

1. Agent generates draft entry
2. System pauses and displays draft
3. Human reviews and approves/rejects/edits
4. Workflow continues or restarts based on decision

## Extending the System

To add a new agent:

1. Create agent file in `agents/` directory
2. Inherit from base functionality
3. Implement required methods
4. Register in orchestrator
5. Add configuration options if needed
6. Update this documentation

## Testing

Each agent should have corresponding tests:

```bash
tests/
├── test_git_analysis.py
├── test_content_generation.py
├── test_fact_checking.py
├── test_quality_assurance.py
├── test_validator.py
└── test_orchestrator.py
```

## Performance Considerations

- Git analysis can be expensive for large repos; uses caching
- Content generation is the most time-intensive; parallelized where possible
- Network calls (e.g., to OpenCode) have timeouts and retries
- Results are cached in `utils/cache.py` to avoid redundant work

## Security

- Git data is read-only; agents never modify repositories
- Configuration is stored in `~/.journalrc` with appropriate permissions
- OpenCode credentials are not logged or stored in generated content
