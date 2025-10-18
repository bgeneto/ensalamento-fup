# Project: Sistema de Ensalamento FUP/UnB

## 🛠️ Required Development Tools

**IMPORTANT**: When working in the shell, you MUST use these tools for the specified tasks:

### File & Code Search Tools
- **Finding FILES**: ALWAYS use `fd` (never use `find`)
```bash
  # Example: Find all TypeScript files
  fd -e ts -e tsx
```

- **Finding TEXT/strings**: ALWAYS use `rg` (ripgrep, never use `grep`)
```bash
  # Example: Search for "TaskStatus" in all files
  rg "TaskStatus" --type ts
```

- **Finding CODE STRUCTURE**: ALWAYS use `ast-grep` for semantic code search
```bash
  # Example: Find all React components with useState
  ast-grep --pattern 'const [$STATE, $SETTER] = useState($INIT)'
```

### Interactive & Data Tools
- **Selecting from MULTIPLE results**: ALWAYS pipe to `fzf` for interactive selection
```bash
  # Example: Interactively select a file to edit
  fd -e tsx | fzf
```

- **Interacting with JSON**: ALWAYS use `jq`
```bash
  # Example: Extract package.json dependencies
  jq '.dependencies' package.json
```

- **Interacting with YAML or XML**: ALWAYS use `yq`
```bash
  # Example: Read a value from YAML config
  yq '.database.host' config.yml
```

### Why These Tools?
- **Performance**: These tools are 10-100x faster than traditional alternatives
- **Accuracy**: Better results with smart filtering and fuzzy matching
- **Developer Experience**: Modern, user-friendly interfaces
- **Project Standard**: Required for consistency across the codebase


## 📋 Documentation Index

### Core Project Documents
- **[REQUIREMENTS.md](docs/REQUIREMENTS.md)** - Full product requirements, features, and priorities
- **[TECH_STACK.md](docs/TECH_STACK.md)** - Technology choices and rationale
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design patterns
- **[SRS.md](docs/SRS.md)** Software Requirements Specification (THIS IS THE MOST IMPORTANT FILE!)


## 📝 Notes for Claude Code

### Shell Command Requirements
**CRITICAL**: You MUST follow these tool requirements for ALL shell operations:
- ❌ NEVER use: `find`, `grep`, `locate`, `ack`
- ✅ ALWAYS use: `fd`, `rg`, `ast-grep`, `fzf`, `jq`, `yq` (as specified above)

### Support/Instructions Files
- When in doubt about features, check docs/REQUIREMENTS.md for priority
- Follow the component structure defined in docs/ARCHITECTURE.md
- Check docs/TECH_STACK.md
- Check SRS.md for Software Requirements Specification
- Check  docs/streamlit-authenticator.md for authentication implementations instructions
- Check docs/ensalamento.md for an example of a final reservation of a room with location, hours, disciplines etc…

