# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated testing and PyPI publishing.

## Workflows

### 1. Test Workflow (`test.yml`)

**Purpose**: Run the test suite across multiple Python versions and operating systems.

**Triggers**:
- Manually via GitHub Actions UI (workflow_dispatch)
- On pull requests to main branch
- On pushes to main branch

**What it does**:
- Tests on Ubuntu, macOS, and Windows
- Tests Python versions 3.8, 3.9, 3.10, 3.11, and 3.12
- Runs pytest with coverage reporting
- Uploads coverage to Codecov (optional)

**To run manually**:
1. Go to the "Actions" tab in your GitHub repository
2. Select "Run Tests" workflow
3. Click "Run workflow" button
4. Select the branch and click "Run workflow"

### 2. PyPI Publishing Workflow (`publish-to-pypi.yml`)

**Purpose**: Build and publish the package to PyPI when a release is created.

**Triggers**:
- Automatically when a GitHub Release is published
- Manually via GitHub Actions UI (for testing with TestPyPI)

**What it does**:
- Builds the distribution packages (wheel and source)
- Publishes to PyPI on release
- Publishes to TestPyPI on manual trigger (for testing)

## Setting up PyPI Publishing

You have two options for authenticating with PyPI:

### Option 1: Trusted Publishing (Recommended)

Trusted publishing uses OpenID Connect (OIDC) and doesn't require storing secrets.

1. Go to your [PyPI account settings](https://pypi.org/manage/account/publishing/)
2. Scroll to "Pending publishers" or "Add a new pending publisher"
3. Fill in:
   - **PyPI Project Name**: `progressBarDistributed`
   - **Owner**: `rsanchezgarc` (your GitHub username/org)
   - **Repository name**: `progressBarDistributed`
   - **Workflow name**: `publish-to-pypi.yml`
   - **Environment name**: `pypi`
4. Click "Add"

For TestPyPI, repeat the process at [test.pypi.org](https://test.pypi.org/manage/account/publishing/) with environment name `testpypi`.

### Option 2: API Token

If you prefer using an API token:

1. Generate a PyPI API token:
   - Go to [PyPI Account Settings](https://pypi.org/manage/account/)
   - Scroll to "API tokens"
   - Click "Add API token"
   - Name it (e.g., "GitHub Actions")
   - Set scope to "Entire account" or specific project

2. Add the token to GitHub Secrets:
   - Go to your repository Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI token (starts with `pypi-`)
   - Click "Add secret"

3. Update `publish-to-pypi.yml`:
   - Uncomment the line: `password: ${{ secrets.PYPI_API_TOKEN }}`
   - Comment out or remove the trusted publishing configuration

Repeat for TestPyPI with `TEST_PYPI_API_TOKEN` if needed.

## Creating a Release

To trigger the PyPI publishing workflow:

1. Go to your repository on GitHub
2. Click on "Releases" → "Create a new release"
3. Click "Choose a tag" and create a new tag (e.g., `v25.09.02`)
4. Fill in release title and description
5. Click "Publish release"

The workflow will automatically:
- Build the package
- Run tests (if configured)
- Upload to PyPI

## Testing the Release Process

Before creating a real release, you can test with TestPyPI:

1. Go to Actions tab
2. Select "Publish to PyPI" workflow
3. Click "Run workflow"
4. This will publish to TestPyPI instead

Then install and test from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ progressBarDistributed
```

## Environment Configuration

The workflows use GitHub Environments for additional protection:

1. Go to Settings → Environments
2. Create two environments:
   - `pypi` - for production PyPI releases
   - `testpypi` - for test releases
3. (Optional) Add protection rules:
   - Required reviewers
   - Wait timer
   - Deployment branches (e.g., only `main`)

## Troubleshooting

### Tests fail on certain platforms

Check the test output in the Actions tab. Some tests may need platform-specific adjustments.

### PyPI publishing fails with authentication error

- If using trusted publishing: Verify the publisher configuration in PyPI matches exactly
- If using API token: Verify the secret name matches what's in the workflow
- Check that the environment names match (`pypi` and `testpypi`)

### Package already exists error

The workflow uses `skip-existing: true` to avoid errors if the version already exists. To release a new version, update the version number in `progressBarDistributed/__init__.py`.

## Workflow Status Badges

Add these badges to your README.md:

```markdown
![Tests](https://github.com/rsanchezgarc/progressBarDistributed/actions/workflows/test.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/progressBarDistributed)
![Python Versions](https://img.shields.io/pypi/pyversions/progressBarDistributed)
```
