# Journal Automation System

Complete OpenCode-powered multi-agent system for automated daily journal generation.

## System Architecture

```
Cron (11:25 AM)
    ↓
OrchestratorAgent (OpenCode-powered coordinator)
    ↓
├─→ GitAnalysisAgent (Python) [commits git_data.json]
├─→ ContentGenerationAgent (OpenCode) [generates journal draft]
├─→ FactCheckingAgent (OpenCode, parallel) [validates]
└─→ QualityAssuranceAgent (OpenCode, parallel) [commits final entry]
```

## Features

✅ **Fully Automated** - Generates complete journal entries from git commits
✅ **OpenCode-Powered** - LLM generates high-quality summaries and validation
✅ **Parallel Execution** - Fact-checking and QA run concurrently
✅ **Commit-As-You-Go** - Each agent stages and commits their work immediately
✅ **Intelligent Retry** - OpenCode LLM decides retry vs. abort strategies
✅ **Failure-Only Notifications** - Desktop alerts only on errors
✅ **Resilient** - Cron failures are caught up on next successful run

## Installation

```bash
# System already installed at: ~/.local/share/journal-automation/

# CLI available at: ~/.local/share/journal-automation/main.py

# Test with a past date
python3 ~/.local/share/journal-automation/main.py generate --date 2025-12-31
```

## Usage

```bash
# Generate journal entry for specific date
python3 ~/.local/share/journal-automation/main.py generate --date YYYY-MM-DD

# Validate existing entry
python3 ~/.local/share/journal-automation/main.py validate --file YYYY/MM/DD.md

# Run orchestrator (for cron)
python3 ~/.local/share/journal-automation/main.py run --date YYYY-MM-DD

# Check entry status
python3 ~/.local/share/journal-automation/main.py status --date YYYY-MM-DD
```

## Cron Setup

```bash
# Run setup script
bash ~/.local/share/journal-automation/cron-setup.sh

# Or manually add to crontab:
25 11 * * * /usr/bin/python3 ~/.local/share/journal-automation/main.py run --date $(date +\%Y-\%m-\%d) >> ~/.local/share/journal-automation/logs/journal.log 2>&1
```

## Agents

### 1. GitAnalysisAgent (Python)
Extracts raw commit data from all repositories:
- Commits by repo
- LOC changes (added/deleted)
- Commit categorization (feat, fix, refactor, etc.)
- Timestamp extraction for hour estimation
- Project descriptions from READMEs

### 2. ContentGenerationAgent (OpenCode)
Generates professional journal content:
- High-level summary (2-3 sentences)
- Project sections with thematic grouping
- Activity summary (5-8 numbered points)
- Projects legend verification
- Uses prompts/ templates for consistency

### 3. FactCheckingAgent (OpenCode)
Validates accuracy and completeness:
- Commit count verification
- Completeness checks (all repos included)
- Consistency validation (LOC, timestamps)
- Duplicate detection
- Anomaly identification
- Returns JSON with reasoning

### 4. QualityAssuranceAgent (OpenCode)
Validates content quality and commits:
- Markdown syntax validation
- Content quality review (writing, formatting)
- Cross-reference checks
- File creation (YYYY/MM/DD.md)
- Git integration (stage + commit)
- Returns detailed assessment

### 5. OrchestratorAgent (OpenCode)
Coordinates all agents with intelligent decisions:
- Work day detection
- Parallel agent execution (where safe)
- Commit-as-you-go pattern
- Retry decisions via LLM reasoning
- Error recovery strategies
- Failure notifications

### 6. CommitAgent (Python)
Handles git operations:
- Stage and commit files
- Generate professional commit messages
- Handle auto_push if configured
- Return success/failure status

## Configuration

Edit `~/.journalrc`:

```json
{
  "general": {
    "author_name": "Josh Wren",
    "code_directory": "/home/josh/code",
    "journal_directory": "/home/josh/code/journal"
  },
  "opencode": {
    "model": "glm-4.7-free",
    "max_workers": 5
  },
  "quality": {
    "min_commits_for_section": 3,
    "commit_as_they_go": true,
    "parallel_agents": true
  }
}
```

## Resilience Features

**Cron Failure Handling:**
- System remembers last processed date
- On next successful run, catches up on missed days
- No manual intervention needed
- Schedule: 11:25 AM daily (early enough to catch missed days from previous day)

**OpenCode Unavailable:**
- Automatic server startup check
- Retry with backoff if server fails
- Fallback to template-based generation if retries exhausted
- Logs failure for later retry

**Git Conflicts:**
- Each agent commits separately (reduces conflicts)
- Orchestrator handles final merge if needed
- Notifications sent only on unresolvable conflicts

## Logs

All logs stored at: `~/.local/share/journal-automation/logs/`

- `journal.log` - Main journal automation log (cron output)
- `journal-automation-YYYYMMDD.log` - Daily rotation logs (Python logging)
- `orchestrator.log` - Main coordination logs
- `agent_errors.log` - Agent failure details
- `notifications.log` - Desktop notification history

## Prompt Templates

All prompts stored at: `~/.local/share/journal-automation/prompts/`

- `summary.txt` - High-level summary generation
- `project_section.txt` - Project section creation
- `fact_checking.txt` - Accuracy validation
- `quality_assurance.txt` - Quality assessment
- `orchestration.txt` - Agent coordination

## Testing

```bash
# Test with December 31, 2025 data
cd ~/.local/share/journal-automation
python3 agents/git_analysis.py  # Test Git Analysis
python3 agents/content_generation.py  # Test Content Generation
python3 agents/fact_checking.py  # Test Fact-Checking
python3 agents/quality_assurance.py  # Test QA
python3 orchestrator.py 2025-12-31  # Test full workflow
```

## Next Steps

1. ✅ System built and installed
2. ✅ Tested with December 2025 data
3. ✅ Set up cron job (11:25 AM daily)
4. ⏭ Monitor first week of operation
5. ⏭ Fine-tune prompts based on output quality
