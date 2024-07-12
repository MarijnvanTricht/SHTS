#!/bin/bash

# Set variables
SOURCE_FOLDER="$(cd "$(dirname "$0")/SHTS/MAC" && pwd)"
TARGET_FOLDER="$HOME/.config/SHTS"
APP_EXECUTABLE="$TARGET_FOLDER/SHTS"
FILE_EXTENSION="shts"

# Display variables
echo "SOURCE_FOLDER: $SOURCE_FOLDER"
echo "TARGET_FOLDER: $TARGET_FOLDER"
echo "APP_EXECUTABLE: $APP_EXECUTABLE"
echo "FILE_EXTENSION: $FILE_EXTENSION"

# Check if target directory exists and remove it if it does
if [ -d "$TARGET_FOLDER" ]; then
    echo "Target directory exists. Removing it."
    rm -rf "$TARGET_FOLDER"
fi

# Create target directory
mkdir -p "$TARGET_FOLDER"

# Copy folder to target location
cp -r "$SOURCE_FOLDER/"* "$TARGET_FOLDER"

# Create file type and associate with the executable (not directly supported in bash)
# Warning: File associations need to be added manually

echo
echo "WARNING: File associations are not directly supported in this script"
echo "This should be added manually if needed"

echo
echo "Folder copied to target location and file association should be created manually."

# Check if TARGET_FOLDER is already in PATH
if [[ ":$PATH:" != *":$TARGET_FOLDER:"* ]]; then
    # Add TARGET_FOLDER to PATH
    echo "Adding TARGET_FOLDER to PATH."
    export PATH="$PATH:$TARGET_FOLDER"
    # Add the line to .bashrc or .zshrc for persistence
    if [ -n "$BASH_VERSION" ]; then
        echo "export PATH=\"\$PATH:$TARGET_FOLDER\"" >> "$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        echo "export PATH=\"\$PATH:$TARGET_FOLDER\"" >> "$HOME/.zshrc"
    fi
    echo "You need to restart your terminal or source your profile file to update PATH."
fi

echo "End of install of SHTS"

# Pause for user to read messages (not directly possible in bash, but read can be used)
read -p "Press [Enter] to continue..."