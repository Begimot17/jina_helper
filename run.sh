#!/bin/bash
echo "Installing dependencies..."
poetry install --no-root

echo "Starting the application..."
poetry run python -m ui.main_window
