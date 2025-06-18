# Intelligent Text Normalizer Plugin

## Plugin Purpose

The Intelligent Text Normalizer plugin leverages Large Language Models (LLMs) to perform advanced text normalization tasks. Unlike traditional rule-based or statistical text cleaning methods, this plugin can understand natural language instructions to correct errors, rephrase text, ensure consistency, expand abbreviations, and perform other complex normalization based on the provided rules.

It is designed to be flexible, allowing users to define custom normalization requirements for different text columns within their datasets.

## Model

-   **Default Model:** The plugin currently uses `Gensyn/Qwen2.5-0.5B-Instruct`. This is a relatively small, instruction-tuned model suitable for a variety of text generation and normalization tasks.
-   **Downloading and Caching:** The model is downloaded automatically by the `transformers` library from the Hugging Face Hub on its first use. It is then cached locally, typically in your user directory under `~/.cache/huggingface/hub/`.
-   **Internet Connection:** An active internet connection is required the first time the plugin (or specifically, the chosen model) is used, to allow for this download. Subsequent uses will load the model from the local cache, not requiring internet access unless the cache is cleared or the model is updated.

## Parameters

The plugin requires the following parameters:

1.  `columns`
    *   **Type:** `list` of `str`
    *   **Required:** Yes
    *   **Description:** A list of column names in the DataFrame that contain the text to be normalized. The plugin will iterate through each specified column and apply the normalization rules to the text in each cell of that column.
    *   **Example:** `["product_description", "customer_review_text"]`

2.  `normalization_rules`
    *   **Type:** `str`
    *   **Required:** Yes
    *   **Description:** A natural language string describing the normalization tasks the LLM should perform. The quality and specificity of these rules significantly impact the output.
    *   **Examples:**
        *   "Correct spelling mistakes, fix grammatical errors, and ensure all text is in sentence case."
        *   "Convert all text to lowercase. Remove any punctuation. Expand common street address abbreviations (e.g., 'St.' to 'Street', 'Ave.' to 'Avenue')."
        *   "Rephrase sentences to be more concise. Ensure a professional tone. Remove any informal language or slang."
        *   "Standardize date formats to YYYY-MM-DD. If only a year is present, use YYYY-01-01."

3.  `max_new_tokens` (Optional)
    *   **Type:** `int`
    *   **Default:** `50` (plus the length of the original text)
    *   **Description:** The maximum number of new tokens the LLM can generate as part of the normalized text. This helps control the length of the output and prevent runaway generation. The actual value used internally is `len(original_text) + max_new_tokens` to give enough space for the model to work with.
    *   **Example:** `100`

## Dependencies

This plugin relies on the following core libraries:

-   `transformers>=4.0.0`: For accessing and using Hugging Face models.
-   `torch>=1.8.0`: As a backend for the `transformers` library.
-   `pandas`: For DataFrame manipulation.

These dependencies should be listed in the project's `requirements.txt` and/or `pyproject.toml`.

## Example Usage

### Command Line Interface (CLI) (Conceptual)

If using a CLI tool that supports this plugin system (e.g., `sheetpilot-cli`):

```bash
sheetpilot-cli \
    --input "raw_data.xlsx" \
    --output "normalized_data.xlsx" \
    --module "intelligent_text_normalizer" \
    --params '{
        "columns": ["comments", "feedback_text"],
        "normalization_rules": "Fix all spelling and grammar errors. Ensure the tone is polite and formal. Convert text to title case.",
        "max_new_tokens": 75
    }'
```

### Graphical User Interface (GUI) (Conceptual)

In a GUI application incorporating this plugin:

1.  The "Intelligent Text Normalizer" would be listed as an available data processing module.
2.  Upon selecting it, the user would be presented with configuration options:
    *   A multi-select dropdown or list box to choose the `columns` to process from the loaded dataset.
    *   A text area to input the `normalization_rules`.
    *   Optionally, a field to adjust `max_new_tokens`.
3.  After confirming, the plugin's `process` function would be called with these parameters.

## Troubleshooting and Notes

-   **Processing Speed:** LLM inference can be computationally intensive. Processing large datasets or very long text entries, especially on CPU, can be slow. Consider testing with a sample of your data first.
-   **Model Download Issues:** If the model fails to download on first use:
    *   Check your internet connection.
    *   Verify that Hugging Face Hub (`huggingface.co`) is accessible.
    *   Ensure you have sufficient disk space in your cache directory (`~/.cache/huggingface/hub/`).
    *   The specific model `Gensyn/Qwen2.5-0.5B-Instruct` might be private, require specific access, or have been moved. If issues persist, consider trying a well-known public model like `distilgpt2` for testing connectivity and then confirm the status of the primary model.
-   **Output Quality:** The quality of normalization heavily depends on the clarity of the `normalization_rules` and the capabilities of the chosen LLM. Experiment with different phrasings for your rules.
-   **Memory Usage:** Loading LLMs can consume a significant amount of RAM. Ensure your system has adequate resources.
-   **Error Handling:** The plugin includes basic error handling for model loading and inference per item. If an item fails during normalization, its original text is usually preserved, and an error is logged. Check application logs for details.
-   **Deterministic Output:** While parameters like `temperature` are set to encourage fairly consistent outputs, LLM generation can sometimes have slight variations even with the same input. For critical applications requiring perfect reproducibility, this should be noted.

This README provides a basic guide. For more detailed issues or advanced configuration, you might need to refer to the `transformers` library documentation or the specific model card on Hugging Face Hub.
