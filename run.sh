#!/bin/bash

# The following script is only intended for use in mimi system.
# If the script does not work, this means that some modules changed in mimi system. To fix, update the code or contact the developer.

git fetch
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "No updates available for $DIR_NAME repository."
else
  echo "Updates found for $DIR_NAME repository. Pulling changes..."
  git pull
  echo "Updated $DIR_NAME repository."
fi

export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia

module load Python/3.10.8-GCCcore-12.2.0

# Run the application
python3 mainWindow.py
