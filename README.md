# 8 Sidor Quiz Generator

A small project for learning Swedish using news articles from [8 Sidor](https://8sidor.se/).

This project uses the OpenAI API to turn news articles into **listening comprehension quizzes at the SFI Course C level**, along with multiple-choice questions, useful vocabulary, and common expressions.

## How to Use

1. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file and add your OpenAI API key:

   ```env
   OPENAI_API_KEY=your_api_key
   ```

3. Set your preferences in `main.py`:

   ```python
   category="varlden"
   start_page=1
   max_pages=2
   max_articles=10
   ```

4. Run the program:

   ```bash
   python main.py
   ```

The generated quizzes will be saved as PDFs in the `Quiz/` folder.