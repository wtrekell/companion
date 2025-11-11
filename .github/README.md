# GitHub Actions

This directory contains automated workflows for repository maintenance.

## README Manager

**Workflow:** `readme-manager.yml`
**Purpose:** Automated README file maintenance using Gemini 1.5 Flash AI

### Overview

The README Manager ensures that all directories in the repository have accurate, up-to-date README files that help visitors navigate the content intelligently. It uses Google's Gemini 1.5 Flash model to analyze directory contents and generate or update README files based on templates in `09-templates/readme/`.

### Modes

#### 1. Full Review (Manual)
**Trigger:** Manual via GitHub Actions UI
**Mode:** `full-review`

- Reviews ALL README files across the entire repository
- Updates existing READMEs for accuracy and completeness
- Creates new READMEs where they don't exist
- Works from deepest directories upward

**When to use:**
- After major content reorganization
- When templates have been updated
- For comprehensive documentation refresh

#### 2. Ensure Exists (Manual)
**Trigger:** Manual via GitHub Actions UI
**Mode:** `ensure-exists`

- Checks all directories for README files
- Creates READMEs only where they don't exist
- Does NOT modify existing READMEs
- Works from deepest directories upward

**When to use:**
- Adding documentation to new directory structures
- Initial documentation setup
- After bulk content addition

#### 3. Auto-Update (Automatic)
**Trigger:** Automatic on push to main or claude/** branches
**Mode:** `auto-update`

- Runs automatically when content changes are pushed
- Only processes directories affected by the changes
- Updates READMEs to reflect new, modified, or removed content
- Works from deepest affected directories upward

**When to use:**
- Automatically runs on push (no manual trigger needed)
- Ignores changes to .github/ and *.md files to prevent loops

### Setup

#### Required Secret

You must add a **GEMINI_API_KEY** secret to your repository:

**Getting the API Key:**
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API key" (or "Get API key")
4. Accept the Terms of Service if prompted
5. Copy the generated API key

**Adding to GitHub:**
1. Go to your repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `GEMINI_API_KEY`
4. Value: Paste your Gemini API key
5. Click "Add secret"

**Important Notes:**
- Use Google AI Studio API keys (not Google Cloud Console keys)
- The API key must have access to the Generative Language API
- Free tier has rate limits but should be sufficient for most repositories
- Keep your API key secure - never commit it to the repository

### How to Run Manually

1. Go to the **Actions** tab in your GitHub repository
2. Select **README Manager** from the workflows list
3. Click **Run workflow** button
4. Select the mode:
   - **full-review**: Complete review and update of all READMEs
   - **ensure-exists**: Create READMEs only where missing
5. Click **Run workflow** to start

### How It Works

1. **Directory Analysis**
   - Scans repository structure from deepest directories first
   - Identifies directories with content vs. index directories
   - Collects context about files, subdirectories, and existing READMEs

2. **Template Selection**
   - **Index template**: For directories with subdirectories but no content files
   - **Content template**: For directories containing content files

3. **AI Generation**
   - Uses Gemini 1.5 Flash to analyze directory context
   - Generates professional, clear README content
   - Maintains consistency with repository style and existing documentation

4. **Commit & Push**
   - Commits all README changes with descriptive message
   - Pushes directly to the current branch

### Directory Processing Order

The workflow processes directories from **deepest to shallowest** to ensure that:
- Child directory READMEs are generated before parent directories
- Parent READMEs can reference accurate child README summaries
- The connective tissue between levels requires minimal rework

Example processing order:
```
1. 02-articles/251109-on-authenticity/0901-count-that-couldnt/
2. 02-articles/251109-on-authenticity/0927-algorithmic-theatre/
3. 02-articles/251109-on-authenticity/
4. 02-articles/
5. (root)
```

### Templates Used

- **09-templates/readme/index-directory-readme.md** - For navigation directories
- **09-templates/readme/content-directory-readme.md** - For content directories

### Excluded Directories

The following directories are automatically excluded:
- `.git`, `.github`
- `node_modules`, `__pycache__`
- `.venv`, `venv`
- `.pytest_cache`, `.mypy_cache`
- `dist`, `build`, `.egg-info`

### Monitoring

Check the workflow run logs to see:
- Which directories were processed
- Which READMEs were created vs. updated
- Any errors or warnings
- Final statistics summary

### Troubleshooting

**Workflow not running automatically:**
- Check that changes were pushed to main or claude/** branches
- Verify changes weren't only to .github/ or *.md files (these are ignored)

**API Error: "API_KEY_SERVICE_BLOCKED" or 403 Forbidden:**
This usually means the API key needs to be regenerated or properly configured:
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Delete the old API key if it exists
3. Create a new API key
4. Make sure to accept the Terms of Service
5. Update the GEMINI_API_KEY secret in GitHub with the new key
6. Re-run the workflow

**Other API errors:**
- Verify GEMINI_API_KEY secret is set correctly (check for extra spaces)
- Check API key has sufficient quota (free tier: 15 requests/minute, 1500/day)
- Check you're using a Google AI Studio key, not a Google Cloud key
- Review workflow logs for specific error messages

**READMEs not being generated:**
- Check that directories have actual content (not just .gitkeep)
- Review excluded directories list
- Check workflow logs for processing details
- Verify templates exist in 09-templates/readme/

### Files

```
.github/
├── workflows/
│   └── readme-manager.yml          # GitHub Actions workflow definition
├── scripts/
│   ├── manage_readmes.py          # Python script for README management
│   └── requirements.txt            # Python dependencies
└── README.md                       # This file
```
