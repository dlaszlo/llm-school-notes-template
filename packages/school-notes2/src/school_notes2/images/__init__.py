"""Image generation (plan 4.6, 5.5): a thin wrapper around tools/learning_image.py.

The LLM writes the plan and judges the image; this package budgets, locks, calls the
existing executor, fills the machine fields and inserts the accepted image.
"""
