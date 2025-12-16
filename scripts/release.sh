#!/bin/bash
# Azure HayMaker Release Script
# Creates a tagged release from main and updates README with version links
#
# Usage:
#   ./scripts/release.sh <version>
#   ./scripts/release.sh 1.0.0
#   ./scripts/release.sh 1.2.3 --dry-run
#
# The script will:
#   1. Validate the version format (semantic versioning)
#   2. Ensure we're on main branch with clean working directory
#   3. Update README.md with the new version links
#   4. Commit the README changes
#   5. Create an annotated git tag
#   6. Push the tag and changes to origin

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/rysweet/AzureHayMaker"
DRY_RUN=false

# Parse arguments
VERSION=""
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        *)
            if [[ -z "$VERSION" ]]; then
                VERSION="$arg"
            fi
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

validate_version() {
    local version=$1
    # Semantic versioning regex: MAJOR.MINOR.PATCH with optional pre-release
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$ ]]; then
        log_error "Invalid version format: $version. Use semantic versioning (e.g., 1.0.0, 1.2.3-beta.1)"
    fi
}

check_prerequisites() {
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
    fi

    # Check if we're on main branch
    local current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]]; then
        log_error "Must be on main branch to create a release. Currently on: $current_branch"
    fi

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        log_error "Working directory has uncommitted changes. Commit or stash them first."
    fi

    # Pull latest changes
    log_info "Pulling latest changes from origin/main..."
    git pull origin main

    # Check if tag already exists
    if git tag -l "v$VERSION" | grep -q "v$VERSION"; then
        log_error "Tag v$VERSION already exists. Choose a different version."
    fi
}

get_previous_version() {
    # Get the most recent version tag
    git describe --tags --abbrev=0 2>/dev/null || echo "none"
}

update_readme() {
    local version=$1
    local readme="README.md"

    log_info "Updating README.md with version $version..."

    # Check if version badges section exists
    if grep -q "<!-- VERSION_BADGES_START -->" "$readme"; then
        # Update existing version section
        sed -i "/<!-- VERSION_BADGES_START -->/,/<!-- VERSION_BADGES_END -->/c\\
<!-- VERSION_BADGES_START -->\\
[![Latest Release](https://img.shields.io/badge/release-v${version}-green)](${REPO_URL}/releases/tag/v${version})\\
[![Development](https://img.shields.io/badge/dev-main-orange)](${REPO_URL}/tree/main)\\
\\
> **Version Links:**\\
> - [Latest Stable Release (v${version})](${REPO_URL}/releases/tag/v${version}) - Recommended for production\\
> - [Development Branch (main)](${REPO_URL}/tree/main) - Latest features, may be unstable\\
<!-- VERSION_BADGES_END -->" "$readme"
    else
        # Insert version badges after the first set of badges
        local temp_file=$(mktemp)
        awk -v version="$version" -v repo="$REPO_URL" '
        /^\[!\[License/ && !inserted {
            print
            print ""
            print "<!-- VERSION_BADGES_START -->"
            print "[![Latest Release](https://img.shields.io/badge/release-v" version "-green)](" repo "/releases/tag/v" version ")"
            print "[![Development](https://img.shields.io/badge/dev-main-orange)](" repo "/tree/main)"
            print ""
            print "> **Version Links:**"
            print "> - [Latest Stable Release (v" version ")](" repo "/releases/tag/v" version ") - Recommended for production"
            print "> - [Development Branch (main)](" repo "/tree/main) - Latest features, may be unstable"
            print "<!-- VERSION_BADGES_END -->"
            inserted=1
            next
        }
        {print}
        ' "$readme" > "$temp_file"
        mv "$temp_file" "$readme"
    fi

    log_success "README.md updated with version links"
}

create_release() {
    local version=$1

    if [[ "$DRY_RUN" == true ]]; then
        log_warning "DRY RUN - Would perform the following actions:"
        echo "  1. Update README.md with version $version"
        echo "  2. Commit: 'release: Prepare v$version'"
        echo "  3. Create tag: v$version"
        echo "  4. Push to origin with tags"
        return
    fi

    # Update README
    update_readme "$version"

    # Commit the README changes
    log_info "Committing README changes..."
    git add README.md
    git commit -m "release: Prepare v$version

- Update version badges and links in README
- Set latest stable release to v$version

🤖 Generated with [Claude Code](https://claude.com/claude-code)"

    # Create annotated tag
    log_info "Creating tag v$version..."
    git tag -a "v$version" -m "Release v$version

Azure HayMaker version $version

See CHANGELOG.md for release notes."

    # Push changes and tag
    log_info "Pushing to origin..."
    git push origin main
    git push origin "v$version"

    log_success "Release v$version created successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Create GitHub Release: ${REPO_URL}/releases/new?tag=v${version}"
    echo "  2. Add release notes from CHANGELOG.md"
    echo "  3. Publish the release"
}

# Main script
main() {
    echo ""
    echo "========================================"
    echo "  Azure HayMaker Release Script"
    echo "========================================"
    echo ""

    # Validate arguments
    if [[ -z "$VERSION" ]]; then
        echo "Usage: $0 <version> [--dry-run]"
        echo ""
        echo "Examples:"
        echo "  $0 1.0.0           # Create release v1.0.0"
        echo "  $0 1.2.3-beta.1    # Create pre-release"
        echo "  $0 2.0.0 --dry-run # Preview without making changes"
        echo ""
        exit 1
    fi

    validate_version "$VERSION"

    local previous=$(get_previous_version)
    log_info "Previous version: $previous"
    log_info "New version: $VERSION"

    if [[ "$DRY_RUN" == true ]]; then
        log_warning "Running in DRY RUN mode - no changes will be made"
    else
        check_prerequisites
    fi

    echo ""
    read -p "Proceed with release v$VERSION? [y/N] " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "Release cancelled"
        exit 0
    fi

    create_release "$VERSION"
}

# Run main function
main
