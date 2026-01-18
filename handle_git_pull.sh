#!/bin/bash
# Script to handle git pull when run_tests.sh has local changes

echo "Handling git pull with local changes to run_tests.sh..."
echo ""

# Check current status
echo "Current status:"
git status run_tests.sh
echo ""

# Option 1: Stash, pull, then reapply
echo "Stashing local changes..."
git stash push -m "Stash run_tests.sh before pull" run_tests.sh

echo ""
echo "Pulling from remote..."
git pull origin dev --no-rebase

echo ""
echo "Reapplying stashed changes..."
git stash pop

echo ""
echo "Checking for conflicts..."
if git status run_tests.sh | grep -q "both modified"; then
    echo "⚠️  CONFLICT DETECTED in run_tests.sh"
    echo "You'll need to manually resolve the conflict."
    echo "Run: git status to see the conflict"
else
    echo "✅ No conflicts - changes applied successfully!"
fi
