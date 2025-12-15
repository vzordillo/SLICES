#!/bin/bash
# Git Checkpoint Script
# Creates incremental tags at each major phase for easy rollback

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <checkpoint-name>"
    echo "Example: $0 checkpoint-phase1-test-structure"
    echo ""
    echo "Available checkpoint names:"
    echo "  checkpoint-phase0-initial"
    echo "  checkpoint-phase1-test-structure"
    echo "  checkpoint-phase1-test-config"
    echo "  checkpoint-phase1-fixtures"
    echo "  checkpoint-phase2-encoding-tests"
    echo "  checkpoint-phase2-decoding-tests"
    echo "  checkpoint-phase2-validation-tests"
    echo "  checkpoint-phase2-tobascco-tests"
    echo "  checkpoint-phase3-round-trip"
    echo "  checkpoint-phase3-mlip-tests"
    echo "  checkpoint-phase3-moved-tests"
    echo "  checkpoint-phase4-regression"
    echo "  checkpoint-phase4-compatibility"
    echo "  checkpoint-phase5-dirs-created"
    echo "  checkpoint-phase5-files-moved"
    echo "  checkpoint-phase5-code-markers"
    echo "  checkpoint-phase6-api-docs"
    echo "  checkpoint-phase6-user-guides"
    echo "  checkpoint-phase6-dev-docs"
    echo "  checkpoint-phase7-ci"
    echo "  checkpoint-phase7-precommit"
    echo "  checkpoint-phase7-benchmarks"
    exit 1
fi

CHECKPOINT_NAME="$1"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
BRANCH=$(git branch --show-current)

echo "Creating checkpoint: $CHECKPOINT_NAME"
echo "Branch: $BRANCH"
echo "Timestamp: $TIMESTAMP"

# Check if we're on the feature branch
if [[ "$BRANCH" != "feature/testing-and-organization" ]]; then
    echo "Warning: Not on feature/testing-and-organization branch"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if working directory is clean
if ! git diff-index --quiet HEAD --; then
    echo "Warning: Working directory has uncommitted changes"
    git status --short
    read -p "Create checkpoint anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please commit or stash changes first"
        exit 1
    fi
fi

# Create annotated tag
git tag -a "$CHECKPOINT_NAME" -m "Checkpoint: $CHECKPOINT_NAME
Branch: $BRANCH
Timestamp: $TIMESTAMP
Created by: $(whoami)"

echo "✓ Checkpoint tag created: $CHECKPOINT_NAME"
echo ""
echo "To view all checkpoints:"
echo "  git tag -l 'checkpoint-*'"
echo ""
echo "To rollback to this checkpoint:"
echo "  git reset --hard $CHECKPOINT_NAME"
echo ""
echo "Or create a recovery branch:"
echo "  git checkout -b recovery-from-$CHECKPOINT_NAME $CHECKPOINT_NAME"

