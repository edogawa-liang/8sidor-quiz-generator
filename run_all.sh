#!/bin/bash

# Stop if any command fails
set -e

# Go to the project directory
cd "$(dirname "$0")"


# Generate quizzes for each category
for category in sverige varlden vardags; do
    echo "======================================"
    echo "Generating quizzes for: $category"
    echo "======================================"

.venv/bin/python -c "
from main import main

main(
    category='$category',
    start_page=1,
    max_pages=2,
    max_articles=10,
    delay=1,
    model='gpt-4.1-mini',
    use_existing_csv=False
)
"
done

echo "======================================"
echo "All quizzes generated successfully!"
echo "======================================"