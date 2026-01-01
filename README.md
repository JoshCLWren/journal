# Coding Journal

[![CI Status](https://github.com/your-username/journal/workflows/CI/badge.svg)](https://github.com/your-username/journal/actions)

This journal tracks daily coding activity, projects, and development progress across all repositories in `~/code` and `~/vpn-torrent`. It features an AI-powered automation system for generating, validating, and committing journal entries.

## Purpose

- **Track progress**: Log daily commits, features, and achievements
- **Reflect on growth**: Identify patterns, strengths, and areas for improvement  
- **Maintain development history**: Reference past work and decision-making
- **Document skills**: Catalog technical knowledge and problem-solving approaches

## Structure

```
journal/
├── README.md                    # This file
├── 2025/
│   ├── 12.md                    # December 2025 summary
│   ├── 12-feedback.md           # December 2025 feedback analysis
│   └── 12/                      # Daily entries
│       ├── 06.md
│       ├── 07.md
│       ├── 14.md
│       ├── 15.md
│       ├── 21.md
│       ├── 22.md
│       ├── 23.md
│       ├── 24.md
│       ├── 25.md
│       ├── 26.md
│       ├── 27.md
│       ├── 28.md
│       ├── 29.md
│       ├── 30.md
│       └── 31.md
└── 2026/
    └── [future months]
```

## Navigation

### Monthly Summaries
- [December 2025](2025/12.md) - 13 active days, 527 commits

### Daily Entries (December 2025)
- [December 6, 2025](2025/12/06.md) - comics_backend & ebay_assistant launch
- [December 7, 2025](2025/12/07.md) - UI progression & image management
- [December 8-10, 2025](2025/12.md) - No commits
- [December 14, 2025](2025/12/14.md) - eBay description generation
- [December 15, 2025](2025/12/15.md) - API polish
- [December 16-20, 2025](2025/12.md) - No commits
- [December 21, 2025](2025/12/21.md) - OpenCode integration
- [December 22, 2025](2025/12/22.md) - cdisplayagain launch
- [December 23, 2025](2025/12/23.md) - vpn-torrent launch
- [December 24, 2025](2025/12/24.md) - Performance optimization
- [December 25, 2025](2025/12/25.md) - hipcomicscraper launch & pyvips contributions
- [December 26, 2025](2025/12/26.md) - Test coverage expansion
- [December 27, 2025](2025/12/27.md) - Mac compatibility
- [December 28, 2025](2025/12/28.md) - comic-web-scrapers major work
- [December 29, 2025](2025/12/29.md) - Massive refactoring
- [December 30, 2025](2025/12/30.md) - comic-pile & python-starter-template launch
- [December 31, 2025](2025/12/31.md) - AI agent orchestration completion

### Feedback & Analysis
- [December 2025 Feedback](2025/12-feedback.md) - Performance analysis, strengths, and areas for improvement

## Entry Format

Each daily entry follows a consistent structure:

```markdown
# December 31, 2025

**Work Summary:** ~8-10 hours, ~2,500-4,000 lines - Brief description

## Summary
High-level overview of the day's work

## Repositories Worked On
- `~/code/repo-name` (X commits)
- Total: Y commits

## Project Name
**Feature Category**
- Feat: specific feature
- Fix: specific bug fix
- Refactor: code improvement
- Docs: documentation

## Summary of Activity
Recap of key accomplishments

---

## Projects Legend
Brief descriptions of all projects mentioned
```

**Sections:**
- **Header**: Date, estimated hours, lines of code, summary
- **Summary**: High-level overview
- **Repositories**: List of repos with commit counts
- **Detailed breakdown**: By project with categorized commits
- **Projects Legend**: Descriptions of projects referenced

## Commit Message Conventions

Entries follow conventional commit prefixes:
- `Feat:` - New feature
- `Fix:` - Bug fix
- `Refactor:` - Code restructuring
- `Docs:` - Documentation
- `Chore:` - Maintenance tasks
- `Test:` - Test additions
- `Perf:` - Performance improvements

## Automation

The journal includes an AI-powered automation system with:

- **Multi-agent orchestration** for intelligent journal entry generation
- **Git analysis** to extract commit data across multiple repositories
- **Content generation** using AI models (via OpenCode API)
- **Fact checking** and quality assurance
- **Automatic validation** and commit workflow

See [AGENTS.md](AGENTS.md) for detailed documentation of the agent architecture.

## Quick Start

### Setting Up the Automation System

```bash
# Clone the repository
git clone https://github.com/your-username/journal.git
cd journal

# Create virtual environment
make venv

# Install dependencies
make sync

# Install pre-commit hook
make install-githook

# Run automation for today
python main.py generate

# Or for a specific date
python main.py generate --date 2025-12-31
```

### Development Workflow

```bash
# Activate virtual environment
source .venv/bin/activate

# Run linting
make lint

# Run tests
make pytest

# Run the application
python main.py --help
```

## Project Structure

```
journal/
├── README.md                    # This file
├── AGENTS.md                    # Agent architecture documentation
├── CONTRIBUTING.md              # Contribution guidelines
├── main.py                      # CLI entry point
├── config.py                    # Configuration management
├── orchestrator.py              # Main orchestration logic
├── opencode_client.py           # OpenCode API client
├── agents/                      # Agent implementations
│   ├── git_analysis.py
│   ├── content_generation.py
│   ├── fact_checking.py
│   ├── quality_assurance.py
│   ├── validator.py
│   └── orchestrator.py
├── utils/                       # Utility modules
│   ├── cache.py
│   ├── git_utils.py
│   ├── logging_utils.py
│   ├── markdown_utils.py
│   └── opencode_utils.py
├── prompts/                     # AI prompt templates
├── scripts/                     # Utility scripts
│   └── lint.sh
├── tests/                       # Test suite
│   ├── conftest.py
│   └── test_config.py
├── .github/                     # CI/CD configuration
│   └── workflows/ci.yml
├── 2025/                        # Journal entries
│   ├── 12.md
│   ├── 12-feedback.md
│   └── 12/
└── 2026/                        # Future entries
```

## Configuration

Configuration is stored in `~/.journalrc`. The first time you run the application, it will create a default configuration file.

Key settings:
- `code_directory`: Base directory for code repositories (default: `~/code`)
- `journal_directory`: Directory for journal entries (default: `~/code/journal`)
- `git.exclude_repos`: Repositories to exclude from analysis
- `opencode.model`: AI model to use for content generation
- `quality.require_human_approval`: Whether to require manual approval before committing

See `config.py` for full configuration options.

## December 2025 Highlights

**Productivity**
- 527 total commits across 9 projects
- 13 active development days
- 174 commits on busiest day (Dec 31)

**Major Projects**
- comic-pile - AI agent orchestration system
- cdisplayagain - Comic reader (96% test coverage)
- comic-web-scrapers - Multi-source scraping with ML
- comics_backend - FastAPI backend for eBay
- python-starter-template - Reusable project scaffolding

**Notable Contributions**
- Type hints contributed to pyvips 3.2.0 (upstream PR)
- Production-grade Task API for AI agent coordination
- Smart preloading algorithm for 2x performance improvement

## Adding New Entries

For a new daily entry:

1. Navigate to the appropriate directory: `YYYY/MM/`
2. Create new entry: `DD.md`
3. Follow entry format structure
4. Include work summary with hours/LOC estimate
5. List all repositories worked on with commit counts
6. Categorize commits by project
7. Add projects legend for new projects
8. Update monthly index with link to new entry
9. Update this README with link to new day

## Code Quality

This project follows strict code quality standards:

- **Python 3.13** with type hints throughout
- **ruff** for linting and formatting (line length: 100)
- **pyright** for static type checking
- **Pre-commit hooks** that enforce code quality standards
- **pytest** for testing with coverage reporting

### Linting

```bash
# Run all linting checks
make lint

# Format code with ruff
ruff format .
```

### Type Checking

```bash
# Run type checker
pyright .
```

### Testing

```bash
# Run all tests
make pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## CI/CD

GitHub Actions runs on every push to main and on pull requests:

- **Lint job**: Runs ruff and pyright
- **Tests job**: Runs pytest with coverage

View pipeline status in the Actions tab of the repository.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see LICENSE file for details
