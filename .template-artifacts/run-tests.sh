#!/bin/bash

# Script to copy pyproject.toml, replace placeholders, and run tests
# This script works entirely within the .template-artifacts folder without modifying main project files

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="$SCRIPT_DIR/../pyproject.toml"
LOCAL_PYPROJECT="$SCRIPT_DIR/pyproject.toml"

# Default values (can be overridden by environment variables)
APP_NAME="${APPLICATION_NAME_HYPHEN:-mcp-template-base}"
DESCRIPTION="${DESCRIPTION:-MCP Template Base Application}"

echo "Step 1: Copying pyproject.toml into .template-artifacts folder..."
echo "  Source: $SOURCE_FILE"
echo "  Destination: $LOCAL_PYPROJECT"

# Check if source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: Source file not found at $SOURCE_FILE"
    exit 1
fi

# Copy the original file to .template-artifacts folder
cp "$SOURCE_FILE" "$LOCAL_PYPROJECT"

echo "Step 2: Replacing placeholders in local copy..."
echo "  App Name: $APP_NAME"
echo "  Description: $DESCRIPTION"

# Replace placeholders using sed
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed syntax
    sed -i '' "s/\${{GLOBAL:APPLICATION_NAME_HYPHEN}}/$APP_NAME/g" "$LOCAL_PYPROJECT"
    sed -i '' "s/\${{DESCRIPTION}}/$DESCRIPTION/g" "$LOCAL_PYPROJECT"
else
    # Linux sed syntax
    sed -i "s/\${{GLOBAL:APPLICATION_NAME_HYPHEN}}/$APP_NAME/g" "$LOCAL_PYPROJECT"
    sed -i "s/\${{DESCRIPTION}}/$DESCRIPTION/g" "$LOCAL_PYPROJECT"
fi

echo "Successfully replaced placeholders in local pyproject.toml"

# Display the changes made
echo ""
echo "Updated content preview:"
echo "======================"
grep -E "^name|^description" "$LOCAL_PYPROJECT" || true
echo "======================"

echo ""
echo "Step 3: Creating symbolic link and running tests..."

# Change to the project root directory
cd "$SCRIPT_DIR/.."

# Create a temporary symbolic link to use our modified pyproject.toml
if [ -L "pyproject.toml.orig" ]; then
    rm "pyproject.toml.orig"
fi

# Backup original and create symlink to our modified version
mv "pyproject.toml" "pyproject.toml.orig"
ln -s ".template-artifacts/pyproject.toml" "pyproject.toml"

# Function to restore original file on exit
cleanup() {
    echo ""
    echo "Restoring original pyproject.toml..."
    if [ -L "pyproject.toml" ]; then
        rm "pyproject.toml"
    fi
    if [ -f "pyproject.toml.orig" ]; then
        mv "pyproject.toml.orig" "pyproject.toml"
        echo "Original file restored"
    fi
    # Clean up the local copy
    if [ -f "$LOCAL_PYPROJECT" ]; then
        rm "$LOCAL_PYPROJECT"
        echo "Local pyproject.toml copy cleaned up"
    fi
}

# Set trap to restore file on script exit (success or failure)
trap cleanup EXIT

# Run uv sync and tests
echo "Installing dependencies with modified pyproject.toml..."
uv sync

echo "Running unit tests..."
uv run nox -s tests

echo "Running integration tests..."
uv run nox -s integrations

echo ""
echo "All tests completed successfully!"
