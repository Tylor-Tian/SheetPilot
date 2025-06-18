import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import logging

# Import the module to be tested
# Assuming plugins are discoverable via python path additions or a proper package structure
# For this test, we might need to adjust path if plugins are not directly importable
try:
    from plugins.intelligent_text_normalizer import process, format_prompt, parse_llm_output
    PLUGIN_AVAILABLE = True
except ImportError as e:
    print(f"Import Error: {e}. Make sure plugin is in PYTHONPATH or installed.")
    PLUGIN_AVAILABLE = False
    # Define dummy functions if plugin not available, so tests can be skipped gracefully
    def process(df, **params): return df
    def format_prompt(text, rules): return ""
    def parse_llm_output(output, prompt): return ""


# Skip all tests in this file if the plugin module isn't available
pytestmark = pytest.mark.skipif(not PLUGIN_AVAILABLE, reason="IntelligentTextNormalizer plugin not found or dependencies missing.")

# Sample Data for testing
@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'text_col1': ["Ths is a tst.", "anothr example with errrs.", "  extra spaces  "],
        'text_col2': ["pls fix this asap", "keep this", "ALL CAPS TEXT"],
        'other_col': [1, 2, 3]
    })

# --- Test format_prompt ---
def test_format_prompt():
    text = "Test input"
    rules = "Convert to uppercase."
    expected_prompt = (
        f"Please normalize the following text based on these rules: '{rules}'.\n"
        f"Original text: '''{text}'''\n"
        f"Return only the normalized text, with no additional explanation, labels, or markdown formatting.\n"
        f"Normalized text:"
    )
    assert format_prompt(text, rules) == expected_prompt

# --- Test parse_llm_output ---
@pytest.mark.parametrize("llm_full_output, prompt_text, expected_extraction", [
    ("Prompt was: ... Normalized text: This is normalized.", "Prompt was: ... Normalized text:", "This is normalized."),
    ("Normalized text: Clean output.", "Some prompt Normalized text:", "Clean output."),
    ("Normalized text:Output with<|endoftext|>", "Prompt Normalized text:", "Output with<|endoftext|>"), # Test current behavior, may need refinement in actual parser
    ("This is the full output including the prompt. Normalized text: Extracted part", "This is the full output including the prompt. Normalized text:", "Extracted part"),
    ("No cue here, just output.", "This was the prompt.", "No cue here, just output."), # Fallback test
    ("Normalized text: Leading and trailing spaces ", "Prompt Normalized text:", "Leading and trailing spaces"),
])
def test_parse_llm_output(llm_full_output, prompt_text, expected_extraction):
    # The 'prompt' argument to parse_llm_output is the original prompt sent to LLM.
    # For these tests, we only care about the cue "Normalized text:" within the llm_full_output.
    assert parse_llm_output(llm_full_output, prompt_text) == expected_extraction


# --- Test process function ---

# Mock for the transformers.pipeline object
@patch('plugins.intelligent_text_normalizer.pipeline', autospec=True)
def test_process_success(mock_pipeline_constructor, sample_df):
    # Configure the mock pipeline instance
    mock_llm = MagicMock()
    # Simulate the structure of the pipeline output
    mock_llm.side_effect = [
        # Responses for text_col1
        [{'generated_text': format_prompt("Ths is a tst.", "Fix typos and expand abbreviations") + " This is a test."}],
        [{'generated_text': format_prompt("anothr example with errrs.", "Fix typos and expand abbreviations") + " Another example without errors."}],
        [{'generated_text': format_prompt("  extra spaces  ", "Fix typos and expand abbreviations") + "extra spaces"}],
        # Responses for text_col2
        [{'generated_text': format_prompt("pls fix this asap", "Fix typos and expand abbreviations") + "please fix this as soon as possible"}],
        [{'generated_text': format_prompt("keep this", "Fix typos and expand abbreviations") + "keep this"}], # Explicitly handle "keep this"
        [{'generated_text': format_prompt("ALL CAPS TEXT", "Fix typos and expand abbreviations") + "all caps text"}]
    ]
    mock_pipeline_constructor.return_value = mock_llm

    # Assuming model is successfully loaded for this test
    with patch('plugins.intelligent_text_normalizer.MODEL_PATH_CONFIGURED', True), \
         patch('plugins.intelligent_text_normalizer.llm_pipeline', mock_llm):

        params = {
            "columns": ["text_col1", "text_col2"],
            "normalization_rules": "Fix typos and expand abbreviations" # General rule for mock
        }

        # Create a copy as the function modifies in place (or returns a copy)
        df_to_process = sample_df.copy()
        result_df = process(df_to_process, **params)

        expected_text_col1 = ["This is a test.", "Another example without errors.", "extra spaces"]
        expected_text_col2 = ["please fix this as soon as possible", "keep this", "all caps text"] # "keep this" is not processed by mock

        expected_text_col1 = ["This is a test.", "Another example without errors.", "extra spaces"]
        # After correction, "keep this" should be processed by mock and returned as "keep this"
        expected_text_col2 = ["please fix this as soon as possible", "keep this", "all caps text"]

        pd.testing.assert_series_equal(result_df['text_col1'], pd.Series(expected_text_col1, name='text_col1'), check_dtype=False)
        pd.testing.assert_series_equal(result_df['text_col2'], pd.Series(expected_text_col2, name='text_col2'), check_dtype=False)

        # Check that other_col is unchanged
        pd.testing.assert_series_equal(result_df['other_col'], sample_df['other_col'], check_dtype=False)

        # Verify LLM was called for all 6 items.
        assert mock_llm.call_count == 6


@patch('plugins.intelligent_text_normalizer.pipeline', MagicMock(side_effect=Exception("Model loading failed")))
@patch('plugins.intelligent_text_normalizer.MODEL_PATH_CONFIGURED', False) # Simulate failure
@patch('plugins.intelligent_text_normalizer.llm_pipeline', None) # Simulate failure
def test_process_model_initialization_failure(sample_df, caplog):
    # This test implicitly relies on the global `llm_pipeline` being None and `MODEL_PATH_CONFIGURED` being False
    # due to the patches at the test function level.
    # We need to ensure the module's global state is correctly simulated if it's re-imported or state is tricky.
    # The most direct way is to patch 'plugins.intelligent_text_normalizer.MODEL_PATH_CONFIGURED' and 'plugins.intelligent_text_normalizer.llm_pipeline'

    params = {"columns": ["text_col1"], "normalization_rules": "Fix typos"}

    with caplog.at_level(logging.WARNING):
        result_df = process(sample_df.copy(), **params)

    # DataFrame should be unchanged
    pd.testing.assert_frame_equal(result_df, sample_df)

    # Check for warning log
    assert "LLM model for IntelligentTextNormalizer is not available or not configured." in caplog.text
    assert "Skipping actual LLM processing." in caplog.text

@patch('plugins.intelligent_text_normalizer.pipeline', autospec=True)
def test_process_inference_error_fallback(mock_pipeline_constructor, sample_df, caplog):
    mock_llm = MagicMock()
    # First call works, second raises an error, third works
    mock_llm.side_effect = [
        [{'generated_text': format_prompt("Ths is a tst.", "Fix typos") + " This is a test."}],
        Exception("LLM inference error!"),
        [{'generated_text': format_prompt("  extra spaces  ", "Fix typos") + "extra spaces"}]
    ]
    mock_pipeline_constructor.return_value = mock_llm

    with patch('plugins.intelligent_text_normalizer.MODEL_PATH_CONFIGURED', True), \
         patch('plugins.intelligent_text_normalizer.llm_pipeline', mock_llm):

        params = {"columns": ["text_col1"], "normalization_rules": "Fix typos"}
        df_to_process = sample_df.copy()

        with caplog.at_level(logging.ERROR):
            result_df = process(df_to_process, **params)

        # Check results: first and third processed, second is original due to error
        assert result_df.loc[0, 'text_col1'] == "This is a test."
        assert result_df.loc[1, 'text_col1'] == "anothr example with errrs." # Original
        assert result_df.loc[2, 'text_col1'] == "extra spaces"

        # Verify error log for the failed item
        assert "Error during LLM inference for row 1, column 'text_col1'" in caplog.text
        assert "LLM inference error!" in caplog.text

        # Other columns unchanged
        pd.testing.assert_series_equal(result_df['text_col2'], sample_df['text_col2'])
        pd.testing.assert_series_equal(result_df['other_col'], sample_df['other_col'])

@patch('plugins.intelligent_text_normalizer.MODEL_PATH_CONFIGURED', True) # Assume model is loaded
@patch('plugins.intelligent_text_normalizer.llm_pipeline', new_callable=MagicMock) # Mock the pipeline itself
def test_process_invalid_column(mock_llm_pipeline_in_module, sample_df, caplog): # Renamed arg for clarity
    # mock_llm_pipeline_in_module is the MagicMock instance replacing plugins.intelligent_text_normalizer.llm_pipeline
    # No LLM calls should happen for the invalid column.

    params = {"columns": ["text_col1", "non_existent_col"], "normalization_rules": "Process it"}
    df_to_process = sample_df.copy()

    # Mock LLM calls for the valid column 'text_col1'
    # Configure the mock directly via the patched object in the module
    mock_llm_pipeline_in_module.side_effect = [
        [{'generated_text': format_prompt(str(sample_df.loc[i, 'text_col1']), "Process it") + f"Processed {i}"}]
        for i in range(len(sample_df)) # This will mock for 3 items in text_col1
    ]

    with caplog.at_level(logging.WARNING):
        result_df = process(df_to_process, **params)

    assert "Column 'non_existent_col' not found in DataFrame. Skipping this column." in caplog.text

    # Check that text_col1 was processed
    for i in range(len(sample_df)):
        assert result_df.loc[i, 'text_col1'] == f"Processed {i}"

    # Other columns should be untouched
    pd.testing.assert_series_equal(result_df['text_col2'], sample_df['text_col2'])
    pd.testing.assert_series_equal(result_df['other_col'], sample_df['other_col'])


def test_process_missing_columns_param(sample_df):
    with pytest.raises(ValueError, match="The 'columns' parameter must be provided"):
        process(sample_df.copy(), normalization_rules="Some rules")

def test_process_missing_rules_param(sample_df, caplog):
    # Assuming MODEL_PATH_CONFIGURED is True, llm_pipeline is mocked
    with patch('plugins.intelligent_text_normalizer.MODEL_PATH_CONFIGURED', True), \
         patch('plugins.intelligent_text_normalizer.llm_pipeline', MagicMock()):

        with caplog.at_level(logging.WARNING):
            result_df = process(sample_df.copy(), columns=["text_col1"])

        assert "The 'normalization_rules' parameter was not provided. Skipping normalization." in caplog.text
        pd.testing.assert_frame_equal(result_df, sample_df)


# Example of how to run one test if needed:
# pytest tests/test_intelligent_text_normalizer.py -k "test_format_prompt"
# pytest tests/test_intelligent_text_normalizer.py -k "test_process_success"
# pytest tests/test_intelligent_text_normalizer.py -k "test_process_model_initialization_failure"
# pytest tests/test_intelligent_text_normalizer.py -k "test_process_inference_error_fallback"
# pytest tests/test_intelligent_text_normalizer.py -k "test_process_invalid_column"
# pytest tests/test_intelligent_text_normalizer.py -k "test_parse_llm_output"
